from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.auth.dependencies import require_customer
from app.models.models import User, WaitlistEntry, ShowSeat
from app.schemas.schemas import WaitlistJoinRequest, WaitlistStatusResponse
from app.services.waitlist import add_to_waitlist

router = APIRouter(tags=["Waitlist"])

@router.post("/shows/{show_id}/waitlist")
def join_show_waitlist(
    show_id: int,
    waitlist_data: WaitlistJoinRequest,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    res = add_to_waitlist(db, show_id, current_user.id, waitlist_data.category)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["message"])
    return res

@router.get("/shows/{show_id}/waitlist/status", response_model=WaitlistStatusResponse)
def get_waitlist_status(
    show_id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    # Find active waitlist entries for this show and user
    entry = db.query(WaitlistEntry).filter(
        WaitlistEntry.show_id == show_id,
        WaitlistEntry.customer_id == current_user.id
    ).order_by(WaitlistEntry.created_at.desc()).first()
    
    if not entry:
        return WaitlistStatusResponse(
            position=0,
            status="none",
            message="You are not on the waitlist for this show"
        )
        
    # Get seat label if offered
    offered_label = None
    if entry.offered_seat_id and entry.offered_seat:
        layout = entry.offered_seat.seat_layout
        offered_label = f"{layout.row_label}-{layout.col_number}"
        
    # Recalculate position relative to other "waiting" entries
    current_pos = entry.position
    if entry.status == "waiting":
        # Count how many "waiting" entries are before this one
        ahead_count = db.query(WaitlistEntry).filter(
            WaitlistEntry.show_id == show_id,
            WaitlistEntry.category == entry.category,
            WaitlistEntry.status == "waiting",
            WaitlistEntry.position < entry.position
        ).count()
        current_pos = ahead_count + 1
        
    return WaitlistStatusResponse(
        position=current_pos,
        status=entry.status,
        offer_expires_at=entry.offer_expires_at,
        offered_seat_id=entry.offered_seat_id,
        offered_seat_label=offered_label,
        message=f"Waitlist status: {entry.status.upper()}"
    )
