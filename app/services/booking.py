import datetime
import uuid
import random
import string
from sqlalchemy.orm import Session
from app.models.models import Booking, BookingSeat, ShowSeat, SeatHold, Show, Event, Venue, User, WaitlistEntry
from app.services.qr_code import generate_qr_base64
from app.services.email import send_booking_confirmation
from app.services.waitlist import process_seat_release

def generate_booking_ref() -> str:
    """Generates a unique random booking reference code."""
    chars = string.ascii_uppercase + string.digits
    code = "".join(random.choices(chars, k=8))
    return f"TKT-{code}"

def create_booking(db: Session, customer_id: int, show_id: int, seat_ids: list[int], claim_waitlist_id: int = None) -> dict:
    """
    Confirms a booking for the selected seats which must be currently held by the user.
    If claim_waitlist_id is provided, validates that the seat was offered to this user via waitlist.
    """
    now = datetime.datetime.utcnow()
    
    # 1. Fetch the show details
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        return {"success": False, "message": "Show not found"}
        
    event = db.query(Event).filter(Event.id == show.event_id).first()
    venue = db.query(Venue).filter(Venue.id == show.venue_id).first()
    customer = db.query(User).filter(User.id == customer_id).first()
    
    if not event or not venue or not customer:
        return {"success": False, "message": "Required entities not found"}

    # If waitlist claim, perform waitlist validations
    waitlist_entry = None
    if claim_waitlist_id:
        waitlist_entry = db.query(WaitlistEntry).filter(
            WaitlistEntry.id == claim_waitlist_id,
            WaitlistEntry.customer_id == customer_id,
            WaitlistEntry.status == "offered"
        ).first()
        if not waitlist_entry:
            return {"success": False, "message": "Invalid or expired waitlist offer"}
            
        if waitlist_entry.offer_expires_at < now:
            return {"success": False, "message": "Waitlist offer has expired"}
            
        # Ensure seat_ids matches the offered seat
        if len(seat_ids) != 1 or seat_ids[0] != waitlist_entry.offered_seat_id:
            return {"success": False, "message": "Seat selection does not match the waitlisted offer"}

    # 2. Check hold status for all seats
    seats_to_book = []
    total_amount = 0.0
    
    for seat_id in seat_ids:
        # Get seat
        seat = db.query(ShowSeat).filter(ShowSeat.id == seat_id, ShowSeat.show_id == show_id).first()
        if not seat:
            return {"success": False, "message": f"Seat {seat_id} not found"}
            
        if seat.status != "held":
            return {"success": False, "message": f"Seat {seat.seat_layout.row_label}-{seat.seat_layout.col_number} is not held"}
            
        # Check hold record
        hold = db.query(SeatHold).filter(SeatHold.show_seat_id == seat_id).first()
        if not hold:
            return {"success": False, "message": f"No active hold for seat {seat.seat_layout.row_label}-{seat.seat_layout.col_number}"}
            
        if hold.customer_id != customer_id:
            return {"success": False, "message": f"Seat {seat.seat_layout.row_label}-{seat.seat_layout.col_number} is held by another user"}
            
        if hold.expires_at < now:
            return {"success": False, "message": f"Hold has expired for seat {seat.seat_layout.row_label}-{seat.seat_layout.col_number}"}
            
        seats_to_book.append((seat, hold))
        # Get category price
        price = show.pricing.get(seat.seat_layout.category, 0.0)
        total_amount += price

    # 3. Transition seats to booked status using optimistic locking
    booking_ref = generate_booking_ref()
    
    try:
        booking = Booking(
            show_id=show_id,
            customer_id=customer_id,
            booking_ref=booking_ref,
            total_amount=total_amount,
            status="confirmed"
        )
        db.add(booking)
        db.commit() # Get booking ID
        
        seat_labels = []
        for seat, hold in seats_to_book:
            # Optimistic lock check
            updated = db.query(ShowSeat).filter(
                ShowSeat.id == seat.id,
                ShowSeat.status == "held",
                ShowSeat.version == seat.version
            ).update(
                {"status": "booked", "version": ShowSeat.version + 1},
                synchronize_session=False
            )
            
            if updated == 0:
                # Concurrency issue
                db.rollback()
                return {"success": False, "message": "Failed to book seats due to concurrency conflict"}
                
            # Add booking seat relationship
            bk_seat = BookingSeat(booking_id=booking.id, show_seat_id=seat.id)
            db.add(bk_seat)
            
            # Delete hold
            db.delete(hold)
            
            seat_labels.append(f"{seat.seat_layout.row_label}-{seat.seat_layout.col_number} ({seat.seat_layout.category})")

        # Mark waitlist as converted if applicable
        if waitlist_entry:
            waitlist_entry.status = "converted"

        db.commit()
        
        # 4. Generate QR code
        qr_base64 = generate_qr_base64(booking_ref)
        
        # 5. Send confirmation email
        seats_str = ", ".join(seat_labels)
        send_booking_confirmation(
            to_email=customer.email,
            booking_ref=booking_ref,
            event_title=event.title,
            date=show.date,
            time=show.time,
            venue_name=venue.name,
            seats_str=seats_str,
            total_amount=total_amount,
            qr_base64=qr_base64
        )
        
        return {
            "success": True,
            "booking_ref": booking_ref,
            "booking_id": booking.id,
            "total_amount": total_amount,
            "message": "Booking confirmed! A ticket with a QR code has been emailed to you."
        }
        
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Error confirming booking: {str(e)}"}

def cancel_booking(db: Session, booking_id: int, customer_id: int) -> dict:
    """
    Cancels a booking, makes seats available again, and triggers the waitlist check.
    """
    # Fetch booking
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.customer_id == customer_id,
        Booking.status == "confirmed"
    ).first()
    
    if not booking:
        return {"success": False, "message": "Booking not found or already cancelled"}
        
    try:
        # Mark booking as cancelled
        booking.status = "cancelled"
        
        # Release the seats
        cancelled_seats = []
        for bk_seat in booking.booking_seats:
            seat = bk_seat.show_seat
            # We don't mark as available immediately yet because we will trigger waitlist.
            # In process_seat_release, it will check if there's someone on the waitlist.
            # If yes, it holds the seat for them. If no, it marks as available.
            cancelled_seats.append(seat)
            
        db.commit()
        
        # For each seat, trigger the waitlist check
        for seat in cancelled_seats:
            process_seat_release(db, booking.show_id, seat)
            
        return {"success": True, "message": "Booking successfully cancelled"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Error cancelling booking: {str(e)}"}
