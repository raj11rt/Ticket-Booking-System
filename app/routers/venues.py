from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth.dependencies import require_admin, get_current_user
from app.models.models import Venue, SeatLayout, User
from app.schemas.schemas import VenueCreate, VenueOut, SeatLayoutOut

router = APIRouter(prefix="/venues", tags=["Venues"])

@router.post("", response_model=VenueOut, status_code=status.HTTP_201_CREATED)
def create_venue(venue_data: VenueCreate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    # Check duplicate venue name
    existing = db.query(Venue).filter(Venue.name == venue_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Venue with this name already exists"
        )
        
    # Create venue
    venue = Venue(name=venue_data.name, address=venue_data.address)
    db.add(venue)
    db.commit()
    db.refresh(venue)
    
    # Create seats layout
    seats = []
    seen_seats = set()
    for seat in venue_data.seats:
        seat_key = (seat.row_label, seat.col_number)
        if seat_key in seen_seats:
            continue
        seen_seats.add(seat_key)
        
        layout = SeatLayout(
            venue_id=venue.id,
            row_label=seat.row_label,
            col_number=seat.col_number,
            category=seat.category
        )
        seats.append(layout)
        
    if seats:
        db.bulk_save_objects(seats)
        db.commit()
        
    return venue

@router.get("", response_model=List[VenueOut])
def list_venues(db: Session = Depends(get_db)):
    return db.query(Venue).all()

@router.get("/{venue_id}", response_model=VenueOut)
def get_venue(venue_id: int, db: Session = Depends(get_db)):
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue

@router.get("/{venue_id}/seats", response_model=List[SeatLayoutOut])
def get_venue_seats(venue_id: int, db: Session = Depends(get_db)):
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return db.query(SeatLayout).filter(SeatLayout.venue_id == venue_id).order_by(SeatLayout.row_label, SeatLayout.col_number).all()
