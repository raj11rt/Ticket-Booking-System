from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth.dependencies import require_organiser
from app.models.models import User, Event, Show, ShowSeat, Venue
from app.schemas.schemas import EventOut, EventRevenueSummary, ShowRevenueSummary

router = APIRouter(prefix="/organiser", tags=["Organiser"])

@router.get("/events", response_model=List[EventOut])
def get_organiser_events(
    current_user: User = Depends(require_organiser),
    db: Session = Depends(get_db)
):
    return db.query(Event).filter(Event.organiser_id == current_user.id).all()

@router.get("/events/{event_id}/summary", response_model=EventRevenueSummary)
def get_event_revenue_summary(
    event_id: int,
    current_user: User = Depends(require_organiser),
    db: Session = Depends(get_db)
):
    # Verify event owner
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    if event.organiser_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this event"
        )
        
    shows = db.query(Show).filter(Show.event_id == event_id).all()
    
    show_summaries = []
    total_event_revenue = 0.0
    
    for s in shows:
        venue = db.query(Venue).filter(Venue.id == s.venue_id).first()
        venue_name = venue.name if venue else "Unknown Venue"
        
        # Count seats
        capacity = db.query(ShowSeat).filter(ShowSeat.show_id == s.id).count()
        
        # Booked seats
        booked_seats = db.query(ShowSeat).filter(
            ShowSeat.show_id == s.id,
            ShowSeat.status == "booked"
        ).all()
        
        tickets_sold = len(booked_seats)
        
        # Compute revenue for this show
        show_revenue = 0.0
        for seat in booked_seats:
            price = s.pricing.get(seat.seat_layout.category, 0.0)
            show_revenue += price
            
        show_summaries.append(ShowRevenueSummary(
            show_id=s.id,
            date=s.date,
            time=s.time,
            venue_name=venue_name,
            total_tickets_sold=tickets_sold,
            revenue=show_revenue,
            capacity=capacity
        ))
        
        total_event_revenue += show_revenue
        
    return EventRevenueSummary(
        event_id=event.id,
        title=event.title,
        shows=show_summaries,
        total_revenue=total_event_revenue
    )
