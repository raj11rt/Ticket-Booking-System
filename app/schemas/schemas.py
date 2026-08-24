from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

# --- AUTH SCHEMAS ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    role: str = "customer"  # admin, organiser, customer

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# --- VENUE & SEAT LAYOUT SCHEMAS ---
class SeatLayoutBase(BaseModel):
    row_label: str
    col_number: int
    category: str

class SeatLayoutOut(SeatLayoutBase):
    id: int
    class Config:
        from_attributes = True

class VenueCreate(BaseModel):
    name: str
    address: str
    seats: List[SeatLayoutBase]

class VenueOut(BaseModel):
    id: int
    name: str
    address: str
    class Config:
        from_attributes = True


# --- EVENT & SHOW SCHEMAS ---
class EventCreate(BaseModel):
    title: str
    type: str  # movie, concert
    description: Optional[str] = None
    poster_url: Optional[str] = None

class EventOut(BaseModel):
    id: int
    title: str
    type: str
    description: Optional[str]
    poster_url: Optional[str]
    organiser_id: int
    class Config:
        from_attributes = True

class ShowCreate(BaseModel):
    venue_id: int
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    pricing: Dict[str, float]  # e.g., {"Premium": 300.0, "Standard": 150.0}

class ShowOut(BaseModel):
    id: int
    event_id: int
    venue_id: int
    date: str
    time: str
    pricing: Dict[str, float]
    venue_name: Optional[str] = None
    event_title: Optional[str] = None
    
    class Config:
        from_attributes = True


# --- SHOW SEAT MAP SCHEMAS ---
class ShowSeatOut(BaseModel):
    id: int
    row_label: str
    col_number: int
    category: str
    price: float
    status: str  # available, held, booked
    hold_expires_in_seconds: Optional[int] = None
    is_mine: Optional[bool] = None

    class Config:
        from_attributes = True


# --- SEAT HOLD SCHEMAS ---
class HoldSeatsRequest(BaseModel):
    seat_ids: List[int]

class HoldSeatsResponse(BaseModel):
    success: bool
    held_seats: List[int]
    expires_at: datetime
    message: str


# --- BOOKING SCHEMAS ---
class BookingConfirmRequest(BaseModel):
    seat_ids: List[int]

class BookingSeatDetail(BaseModel):
    seat_id: int
    row_label: str
    col_number: int
    category: str
    price: float

class BookingOut(BaseModel):
    id: int
    booking_ref: str
    event_title: str
    date: str
    time: str
    venue_name: str
    seats: List[BookingSeatDetail]
    total_amount: float
    status: str
    booked_at: datetime

    class Config:
        from_attributes = True


# --- WAITLIST SCHEMAS ---
class WaitlistJoinRequest(BaseModel):
    category: str

class WaitlistStatusResponse(BaseModel):
    position: int
    status: str  # waiting, offered, expired, converted
    offer_expires_at: Optional[datetime] = None
    offered_seat_id: Optional[int] = None
    offered_seat_label: Optional[str] = None
    message: str


# --- ORGANISER DASHBOARD SCHEMAS ---
class ShowRevenueSummary(BaseModel):
    show_id: int
    date: str
    time: str
    venue_name: str
    total_tickets_sold: int
    revenue: float
    capacity: int

class EventRevenueSummary(BaseModel):
    event_id: int
    title: str
    shows: List[ShowRevenueSummary]
    total_revenue: float

# --- OTP SCHEMAS ---
class LoginResponse(BaseModel):
    otp_required: bool = True
    email: Optional[EmailStr] = None
    message: Optional[str] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    role: Optional[str] = None
    name: Optional[str] = None

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str

