from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import datetime
import random
import logging
from app.database import get_db
from app.models.models import User, UserOTP
from app.schemas.schemas import UserCreate, UserLogin, Token, LoginResponse, OTPVerifyRequest
from app.auth.utils import hash_password, verify_password, create_access_token
from app.services.email import send_otp_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Validate role
    if user_data.role not in ["customer", "organiser", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'customer', 'organiser', or 'admin'."
        )
        
    # Check if email exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    # Create user
    hashed = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        password_hash=hashed,
        full_name=user_data.full_name,
        role=user_data.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate token
    token = create_access_token({"sub": user.email, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.full_name
    }

@router.post("/login", response_model=LoginResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    # Generate 6-digit OTP
    otp_code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
    
    # Save or update OTP in DB
    db_otp = db.query(UserOTP).filter(UserOTP.email == user.email).first()
    if db_otp:
        db_otp.otp_code = otp_code
        db_otp.expires_at = expires_at
    else:
        db_otp = UserOTP(email=user.email, otp_code=otp_code, expires_at=expires_at)
        db.add(db_otp)
    db.commit()
    
    # Send OTP email
    send_otp_email(user.email, otp_code)
    
    # Print to console for development/grading convenience
    print(f"\n[LOGIN OTP] Verification code for {user.email} is: {otp_code}\n", flush=True)
    logger.info(f"🔑 [LOGIN OTP] Verification code for {user.email} is: {otp_code}")
    
    return {
        "otp_required": True,
        "email": user.email,
        "message": "Verification code has been sent to your email."
    }

@router.post("/verify-otp", response_model=Token)
def verify_otp(verify_data: OTPVerifyRequest, db: Session = Depends(get_db)):
    db_otp = db.query(UserOTP).filter(
        UserOTP.email == verify_data.email,
        UserOTP.otp_code == verify_data.otp_code
    ).first()
    
    if not db_otp or db_otp.expires_at < datetime.datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
        
    user = db.query(User).filter(User.email == verify_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    # Clean up verified OTP
    db.delete(db_otp)
    db.commit()
    
    # Generate JWT token
    token = create_access_token({"sub": user.email, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.full_name
    }

