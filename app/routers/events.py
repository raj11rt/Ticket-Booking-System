from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.auth.dependencies import require_organiser, require_any_role
from app.models.models import Event, Show, ShowSeat, SeatLayout, Venue, User
from app.schemas.schemas import EventCreate, EventOut, ShowCreate, ShowOut

router = APIRouter(tags=["Events"])

@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(event_data: EventCreate, current_user: User = Depends(require_organiser), db: Session = Depends(get_db)):
    event = Event(
        title=event_data.title,
        type=event_data.type,
        description=event_data.description,
        poster_url=event_data.poster_url,
        organiser_id=current_user.id
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.get("/events", response_model=List[EventOut])
def list_events(
    type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Event)
    if type:
        query = query.filter(Event.type == type)
    if search:
        query = query.filter(Event.title.ilike(f"%{search}%"))
    return query.all()

@router.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.post("/events/{event_id}/shows", response_model=ShowOut, status_code=status.HTTP_201_CREATED)
def create_show(
    event_id: int,
    show_data: ShowCreate,
    current_user: User = Depends(require_organiser),
    db: Session = Depends(get_db)
):
    # Verify event exists and belongs to organizer (or allows any organizer)
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.organiser_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this event"
        )
        
    # Verify venue exists
    venue = db.query(Venue).filter(Venue.id == show_data.venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
        
    # Fetch venue seat layout to make sure there are seats
    seats_layout = db.query(SeatLayout).filter(SeatLayout.venue_id == show_data.venue_id).all()
    if not seats_layout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Venue has no seat layout. Please configure venue seat layout first."
        )
        
    # Validate pricing keys contain all seat categories in layout
    layout_categories = set(s.category for s in seats_layout)
    for cat in layout_categories:
        if cat not in show_data.pricing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Pricing must specify a price for category '{cat}'."
            )
            
    # Create the show
    show = Show(
        event_id=event_id,
        venue_id=show_data.venue_id,
        date=show_data.date,
        time=show_data.time,
        pricing=show_data.pricing
    )
    db.add(show)
    db.commit()
    db.refresh(show)
    
    # Create ShowSeat entries for this show
    show_seats = []
    for layout in seats_layout:
        show_seat = ShowSeat(
            show_id=show.id,
            seat_layout_id=layout.id,
            status="available",
            version=1
        )
        show_seats.append(show_seat)
        
    db.bulk_save_objects(show_seats)
    db.commit()
    
    return show

@router.get("/events/{event_id}/shows", response_model=List[ShowOut])
def get_event_shows(event_id: int, db: Session = Depends(get_db)):
    shows = db.query(Show).filter(Show.event_id == event_id).all()
    out_shows = []
    for s in shows:
        venue = db.query(Venue).filter(Venue.id == s.venue_id).first()
        event = db.query(Event).filter(Event.id == s.event_id).first()
        out_shows.append(
            ShowOut(
                id=s.id,
                event_id=s.event_id,
                venue_id=s.venue_id,
                date=s.date,
                time=s.time,
                pricing=s.pricing,
                venue_name=venue.name if venue else None,
                event_title=event.title if event else None
            )
        )
    return out_shows

@router.get("/shows/{show_id}", response_model=ShowOut)
def get_show_details(show_id: int, db: Session = Depends(get_db)):
    s = db.query(Show).filter(Show.id == show_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Show not found")
    venue = db.query(Venue).filter(Venue.id == s.venue_id).first()
    event = db.query(Event).filter(Event.id == s.event_id).first()
    return ShowOut(
        id=s.id,
        event_id=s.event_id,
        venue_id=s.venue_id,
        date=s.date,
        time=s.time,
        pricing=s.pricing,
        venue_name=venue.name if venue else None,
        event_title=event.title if event else None
    )
