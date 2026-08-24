import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import WaitlistEntry, ShowSeat, SeatHold, Show, Event, Venue, User
from app.config import settings
from app.services.email import send_waitlist_offer

def add_to_waitlist(db: Session, show_id: int, customer_id: int, category: str) -> dict:
    # Check if show exists
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        return {"success": False, "message": "Show not found"}
        
    # Check if category exists in show pricing
    if category not in show.pricing:
        return {"success": False, "message": f"Category '{category}' does not exist for this show"}
        
    # Check if already on waitlist (active)
    existing = db.query(WaitlistEntry).filter(
        WaitlistEntry.show_id == show_id,
        WaitlistEntry.customer_id == customer_id,
        WaitlistEntry.category == category,
        WaitlistEntry.status.in_(["waiting", "offered"])
    ).first()
    if existing:
        return {"success": False, "message": "You are already active on the waitlist for this category"}
        
    # Get current max position
    max_pos = db.query(func.max(WaitlistEntry.position)).filter(
        WaitlistEntry.show_id == show_id,
        WaitlistEntry.category == category
    ).scalar()
    
    position = (max_pos or 0) + 1
    
    entry = WaitlistEntry(
        show_id=show_id,
        customer_id=customer_id,
        category=category,
        position=position,
        status="waiting"
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    
    return {
        "success": True,
        "entry_id": entry.id,
        "position": position,
        "message": "Successfully joined the waitlist"
    }

def process_seat_release(db: Session, show_id: int, seat: ShowSeat):
    """
    Called when a seat is released (due to booking cancellation).
    Offers the seat to the next person in line for that category.
    """
    # Find the next customer in the waitlist for this show and category
    next_entry = db.query(WaitlistEntry).filter(
        WaitlistEntry.show_id == show_id,
        WaitlistEntry.category == seat.seat_layout.category,
        WaitlistEntry.status == "waiting"
    ).order_by(WaitlistEntry.position.asc()).first()
    
    if not next_entry:
        # No one on the waitlist, seat becomes available
        seat.status = "available"
        seat.version += 1
        db.commit()
        return
        
    # Hold the seat for this waitlisted user
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.WAITLIST_OFFER_TTL_MINUTES)
    
    seat.status = "held"
    seat.version += 1
    
    # Also create a SeatHold entry to prevent other holds and enforce TTL
    # Delete any existing hold first just in case
    db.query(SeatHold).filter(SeatHold.show_seat_id == seat.id).delete()
    
    hold = SeatHold(
        show_seat_id=seat.id,
        customer_id=next_entry.customer_id,
        expires_at=expiry
    )
    db.add(hold)
    
    # Update waitlist entry
    next_entry.status = "offered"
    next_entry.offer_expires_at = expiry
    next_entry.offered_seat_id = seat.id
    db.commit()
    
    # Fetch details for the email
    show = db.query(Show).filter(Show.id == show_id).first()
    event = db.query(Event).filter(Event.id == show.event_id).first() if show else None
    venue = db.query(Venue).filter(Venue.id == show.venue_id).first() if show else None
    customer = db.query(User).filter(User.id == next_entry.customer_id).first()
    
    if show and event and venue and customer:
        price = show.pricing.get(seat.seat_layout.category, 0.0)
        seat_label = f"{seat.seat_layout.row_label}-{seat.seat_layout.col_number}"
        expiry_str = expiry.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # In a real app, this URL points to the frontend page
        claim_url = f"http://localhost:8000/frontend/pages/seat-select.html?show_id={show_id}&claim_waitlist={next_entry.id}"
        
        send_waitlist_offer(
            to_email=customer.email,
            event_title=event.title,
            date=show.date,
            time=show.time,
            venue_name=venue.name,
            seat_label=seat_label,
            price=price,
            offer_expires_at=expiry_str,
            claim_url=claim_url
        )

def expire_waitlist_offers(db: Session):
    """
    Called by the background scheduler to expire waitlist offers that weren't claimed in time.
    """
    now = datetime.datetime.utcnow()
    # Find all offered entries that have expired
    expired_offers = db.query(WaitlistEntry).filter(
        WaitlistEntry.status == "offered",
        WaitlistEntry.offer_expires_at < now
    ).all()
    
    if not expired_offers:
        return
        
    for offer in expired_offers:
        offer.status = "expired"
        
        # Release the seat
        seat = db.query(ShowSeat).filter(ShowSeat.id == offer.offered_seat_id).first()
        if seat:
            # Delete corresponding SeatHold
            db.query(SeatHold).filter(SeatHold.show_seat_id == seat.id).delete()
            # Process next person on the waitlist for this seat
            process_seat_release(db, offer.show_id, seat)
            
    db.commit()
