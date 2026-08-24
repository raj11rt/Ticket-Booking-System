from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
from app.database import get_db
from app.auth.dependencies import require_customer, get_current_user
from app.models.models import Show, ShowSeat, SeatHold, User
from app.schemas.schemas import ShowSeatOut, HoldSeatsRequest, HoldSeatsResponse
from app.services.seat_hold import hold_seats, release_customer_holds, release_expired_holds
from app.auth.utils import decode_access_token

router = APIRouter(tags=["Seats"])

@router.get("/shows/{show_id}/seats", response_model=List[ShowSeatOut])
def get_seat_map(
    show_id: int, 
    authorization: Optional[str] = Header(None), 
    db: Session = Depends(get_db)
):
    # Proactively release any expired holds before showing map
    release_expired_holds(db)
    
    # Check if show exists
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
        
    # Get current user if authorized
    current_user_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = decode_access_token(token)
        if payload:
            email = payload.get("sub")
            user = db.query(User).filter(User.email == email).first()
            if user:
                current_user_id = user.id
                
    # Fetch all seats for this show
    seats = db.query(ShowSeat).filter(ShowSeat.show_id == show_id).all()
    
    results = []
    now = datetime.datetime.utcnow()
    
    for s in seats:
        # Determine price based on category
        price = show.pricing.get(s.seat_layout.category, 0.0)
        
        # Calculate hold metadata
        is_mine = False
        expires_in = None
        if s.status == "held" and s.hold:
            is_mine = (s.hold.customer_id == current_user_id) if current_user_id else False
            if s.hold.expires_at > now:
                expires_in = int((s.hold.expires_at - now).total_seconds())
                
        results.append(ShowSeatOut(
            id=s.id,
            row_label=s.seat_layout.row_label,
            col_number=s.seat_layout.col_number,
            category=s.seat_layout.category,
            price=price,
            status=s.status,
            hold_expires_in_seconds=expires_in,
            is_mine=is_mine
        ))
        
    return results

@router.post("/shows/{show_id}/seats/hold", response_model=HoldSeatsResponse)
def hold_show_seats(
    show_id: int,
    hold_data: HoldSeatsRequest,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    if not hold_data.seat_ids:
        raise HTTPException(status_code=400, detail="No seat IDs provided")
        
    res = hold_seats(db, show_id, hold_data.seat_ids, current_user.id)
    if not res["success"]:
        raise HTTPException(status_code=409, detail=res["message"])
        
    return HoldSeatsResponse(
        success=True,
        held_seats=res["held_seats"],
        expires_at=res["expires_at"],
        message=res["message"]
    )

@router.delete("/shows/{show_id}/seats/hold")
def release_held_seats(
    show_id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    release_customer_holds(db, show_id, current_user.id)
    return {"success": True, "message": "Held seats released"}
