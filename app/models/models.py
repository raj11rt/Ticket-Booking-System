from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="customer")  # admin, organiser, customer
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    bookings = relationship("Booking", back_populates="customer")
    waitlist_entries = relationship("WaitlistEntry", back_populates="customer")
    events = relationship("Event", back_populates="organiser")

class Venue(Base):
    __tablename__ = "venues"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    address = Column(String, nullable=False)
    
    # Relationships
    seats = relationship("SeatLayout", back_populates="venue", cascade="all, delete-orphan")
    shows = relationship("Show", back_populates="venue")

class SeatLayout(Base):
    __tablename__ = "seat_layouts"
    
    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id", ondelete="CASCADE"), nullable=False)
    row_label = Column(String, nullable=False)  # e.g. "A", "B"
    col_number = Column(Integer, nullable=False)  # e.g. 1, 2, 3
    category = Column(String, nullable=False)  # e.g. "Premium", "Standard"
    
    # Enforce uniqueness of row/col in a venue
    __table_args__ = (
        UniqueConstraint("venue_id", "row_label", "col_number", name="uq_venue_seat"),
    )
    
    # Relationships
    venue = relationship("Venue", back_populates="seats")
    show_seats = relationship("ShowSeat", back_populates="seat_layout", cascade="all, delete-orphan")

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)  # e.g. "movie", "concert"
    description = Column(String, nullable=True)
    poster_url = Column(String, nullable=True)
    organiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    organiser = relationship("User", back_populates="events")
    shows = relationship("Show", back_populates="event", cascade="all, delete-orphan")

class Show(Base):
    __tablename__ = "shows"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    time = Column(String, nullable=False)  # HH:MM
    pricing = Column(JSON, nullable=False)  # e.g. {"Standard": 150.0, "Premium": 300.0}
    
    # Relationships
    event = relationship("Event", back_populates="shows")
    venue = relationship("Venue", back_populates="shows")
    seats = relationship("ShowSeat", back_populates="show", cascade="all, delete-orphan")
    waitlist_entries = relationship("WaitlistEntry", back_populates="show", cascade="all, delete-orphan")

class ShowSeat(Base):
    __tablename__ = "show_seats"
    
    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer, ForeignKey("shows.id", ondelete="CASCADE"), nullable=False)
    seat_layout_id = Column(Integer, ForeignKey("seat_layouts.id"), nullable=False)
    status = Column(String, nullable=False, default="available")  # available, held, booked
    version = Column(Integer, nullable=False, default=1)  # For optimistic locking
    
    # Relationships
    show = relationship("Show", back_populates="seats")
    seat_layout = relationship("SeatLayout", back_populates="show_seats")
    hold = relationship("SeatHold", uselist=False, back_populates="show_seat", cascade="all, delete-orphan")
    booking_seats = relationship("BookingSeat", back_populates="show_seat")

class SeatHold(Base):
    __tablename__ = "seat_holds"
    
    id = Column(Integer, primary_key=True, index=True)
    show_seat_id = Column(Integer, ForeignKey("show_seats.id", ondelete="CASCADE"), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    held_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # Relationships
    show_seat = relationship("ShowSeat", back_populates="hold")
    customer = relationship("User")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer, ForeignKey("shows.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    booking_ref = Column(String, unique=True, index=True, nullable=False)
    total_amount = Column(Float, nullable=False)
    qr_code_url = Column(String, nullable=True)  # Or store QR as data URI
    status = Column(String, nullable=False, default="confirmed")  # confirmed, cancelled
    booked_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    show = relationship("Show")
    customer = relationship("User", back_populates="bookings")
    booking_seats = relationship("BookingSeat", back_populates="booking", cascade="all, delete-orphan")

class BookingSeat(Base):
    __tablename__ = "booking_seats"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    show_seat_id = Column(Integer, ForeignKey("show_seats.id"), nullable=False)
    
    # Relationships
    booking = relationship("Booking", back_populates="booking_seats")
    show_seat = relationship("ShowSeat", back_populates="booking_seats")

class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer, ForeignKey("shows.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String, nullable=False)  # Seat category (e.g., Premium, Standard)
    position = Column(Integer, nullable=False)  # Queue order
    status = Column(String, nullable=False, default="waiting")  # waiting, offered, expired, converted
    offer_expires_at = Column(DateTime, nullable=True)
    offered_seat_id = Column(Integer, ForeignKey("show_seats.id"), nullable=True)  # The specific seat offered
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    show = relationship("Show", back_populates="waitlist_entries")
    customer = relationship("User", back_populates="waitlist_entries")
    offered_seat = relationship("ShowSeat")

class UserOTP(Base):
    __tablename__ = "user_otps"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)

