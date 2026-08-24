from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.auth.dependencies import require_customer
from app.models.models import Booking, User, Show, Event, Venue
from app.schemas.schemas import BookingConfirmRequest, BookingOut, BookingSeatDetail
from app.services.booking import create_booking, cancel_booking

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("", response_model=dict)
def confirm_customer_booking(
    booking_data: BookingConfirmRequest,
    show_id: int,
    claim_waitlist_id: Optional[int] = None,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    if not booking_data.seat_ids:
        raise HTTPException(status_code=400, detail="No seat IDs provided")
        
    res = create_booking(
        db=db,
        customer_id=current_user.id,
        show_id=show_id,
        seat_ids=booking_data.seat_ids,
        claim_waitlist_id=claim_waitlist_id
    )
    
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["message"])
        
    return res

@router.get("", response_model=List[BookingOut])
def list_my_bookings(
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    bookings = db.query(Booking).filter(
        Booking.customer_id == current_user.id
    ).order_by(Booking.booked_at.desc()).all()
    
    results = []
    for b in bookings:
        show = db.query(Show).filter(Show.id == b.show_id).first()
        event = db.query(Event).filter(Event.id == show.event_id).first() if show else None
        venue = db.query(Venue).filter(Venue.id == show.venue_id).first() if show else None
        
        seats_details = []
        for bk_seat in b.booking_seats:
            seat = bk_seat.show_seat
            price = show.pricing.get(seat.seat_layout.category, 0.0) if show else 0.0
            seats_details.append(BookingSeatDetail(
                seat_id=seat.id,
                row_label=seat.seat_layout.row_label,
                col_number=seat.seat_layout.col_number,
                category=seat.seat_layout.category,
                price=price
            ))
            
        results.append(BookingOut(
            id=b.id,
            booking_ref=b.booking_ref,
            event_title=event.title if event else "Unknown",
            date=show.date if show else "Unknown",
            time=show.time if show else "Unknown",
            venue_name=venue.name if venue else "Unknown",
            seats=seats_details,
            total_amount=b.total_amount,
            status=b.status,
            booked_at=b.booked_at
        ))
        
    return results

@router.delete("/{booking_id}")
def cancel_customer_booking(
    booking_id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    res = cancel_booking(db, booking_id, current_user.id)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["message"])
    return res

@router.get("/{booking_id}/qr")
def get_booking_qr(
    booking_id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.customer_id == current_user.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    from app.services.qr_code import generate_qr_base64
    qr_base64 = generate_qr_base64(booking.booking_ref)
    return {"qr_base64": qr_base64}
