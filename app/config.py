import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./ticket_booking.db"
    SECRET_KEY: str = "supersecretkeychangeinproduction"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    SEAT_HOLD_TTL_MINUTES: int = 10
    WAITLIST_OFFER_TTL_MINUTES: int = 5
    
    # Email settings (e.g. Resend, Brevo, or SMTP)
    # If set to "console", emails will just print to terminal for testing
    EMAIL_PROVIDER: str = "console" 
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@ticketbooking.example.com"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
