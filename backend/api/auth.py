from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import hash_password, verify_password, create_access_token
from core.rate_limit import rate_limit
from models.user import User
from schemas.user_schema import UserCreate, UserLogin, TokenResponse
from utils.logger import get_logger

logger = get_logger("backend.api.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

# ------ Register User -----
@router.post("/register", response_model=TokenResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Rate limit registration by email to prevent spam (5 attempts per hour per email hash)
    rate_limit(hash(user.email), limit=5, window=3600)
    
    logger.info(f"User registration attempt", extra={"email": user.email})
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        logger.warning(f"Registration failed - email exists", extra={"email": user.email})
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hashed password
    hashed_pw = hash_password(user.password)

    new_user = User(
        name=user.full_name,
        email=user.email,
        password_hash=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate JWT token
    access_token = create_access_token(data={"sub": str(new_user.id)})

    logger.info(f"User registered successfully", extra={"user_id": new_user.id, "email": user.email})
    return TokenResponse(token=access_token)

# ------ Login User -----
@router.post("/login", response_model=TokenResponse)
def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    # Rate limit login attempts to prevent brute force (10 attempts per 5 minutes per email)
    rate_limit(hash(user_credentials.email), limit=10, window=300)
    
    logger.info(f"Login attempt", extra={"email": user_credentials.email})
    
    db_user = (
        db.query(User).filter(User.email == user_credentials.email).first()
    )

    if not db_user or not verify_password(user_credentials.password, db_user.password_hash):
        logger.warning(f"Login failed - invalid credentials", extra={"email": user_credentials.email})
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": str(db_user.id)})

    logger.info(f"Login successful", extra={"user_id": db_user.id, "email": user_credentials.email})
    return TokenResponse(token=access_token)

    

