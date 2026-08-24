import datetime
from sqlalchemy.orm import Session
from app.models.models import ShowSeat, SeatHold
from app.config import settings

def release_expired_holds(db: Session):
    # Proactively expire waitlist offers first so they cycle to the next in queue
    from app.services.waitlist import expire_waitlist_offers
    expire_waitlist_offers(db)
    
    now = datetime.datetime.utcnow()
    # Find all expired holds
    expired_holds = db.query(SeatHold).filter(SeatHold.expires_at < now).all()
    if not expired_holds:
        return
        
    for hold in expired_holds:
        # Get the corresponding seat
        seat = db.query(ShowSeat).filter(ShowSeat.id == hold.show_seat_id).first()
        if seat and seat.status == "held":
            seat.status = "available"
            seat.version += 1
        # Delete the hold
        db.delete(hold)
        
    db.commit()

def hold_seats(db: Session, show_id: int, seat_ids: list[int], customer_id: int) -> dict:
    # First, proactively release any expired holds so we get accurate availability
    release_expired_holds(db)
    
    # Start transaction-like block (SQLAlchemy does this by default on session)
    held_seats = []
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.SEAT_HOLD_TTL_MINUTES)
    
    try:
        for seat_id in seat_ids:
            # Query the seat
            seat = db.query(ShowSeat).filter(ShowSeat.id == seat_id, ShowSeat.show_id == show_id).first()
            if not seat:
                return {"success": False, "message": f"Seat {seat_id} not found for show {show_id}"}
                
            if seat.status != "available":
                # Check if this user already holds it (e.g. waitlist offer hold)
                existing_hold = db.query(SeatHold).filter(
                    SeatHold.show_seat_id == seat_id,
                    SeatHold.customer_id == customer_id,
                    SeatHold.expires_at > datetime.datetime.utcnow()
                ).first()
                if existing_hold:
                    # Extend hold duration
                    existing_hold.expires_at = expires_at
                    held_seats.append(seat_id)
                    continue
                else:
                    return {"success": False, "message": f"Seat {seat.seat_layout.row_label}-{seat.seat_layout.col_number} is not available"}
                
            # Perform optimistic lock update
            updated = db.query(ShowSeat).filter(
                ShowSeat.id == seat_id,
                ShowSeat.status == "available",
                ShowSeat.version == seat.version
            ).update(
                {"status": "held", "version": ShowSeat.version + 1},
                synchronize_session=False
            )
            
            if updated == 0:
                # Concurrency conflict: someone else modified this seat
                db.rollback()
                return {"success": False, "message": f"Seat {seat.seat_layout.row_label}-{seat.seat_layout.col_number} was taken by another user"}
            
            # Create the hold record
            hold = SeatHold(
                show_seat_id=seat_id,
                customer_id=customer_id,
                expires_at=expires_at
            )
            db.add(hold)
            held_seats.append(seat_id)
            
        db.commit()
        return {
            "success": True,
            "held_seats": held_seats,
            "expires_at": expires_at,
            "message": "Seats successfully held"
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Error holding seats: {str(e)}"}

def release_customer_holds(db: Session, show_id: int, customer_id: int):
    # Release any holds for this customer on this show (e.g., checkout abandonment)
    holds = db.query(SeatHold).join(ShowSeat).filter(
        ShowSeat.show_id == show_id,
        SeatHold.customer_id == customer_id
    ).all()
    
    for hold in holds:
        seat = db.query(ShowSeat).filter(ShowSeat.id == hold.show_seat_id).first()
        if seat and seat.status == "held":
            seat.status = "available"
            seat.version += 1
        db.delete(hold)
        
    db.commit()
