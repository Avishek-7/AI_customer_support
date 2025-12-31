from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.security import hash_password, verify_password, create_access_token, decode_access_token
from core.rate_limit import rate_limit
from models.user import User
from schemas.user_schema import UserCreate, UserLogin, TokenResponse, ResetPasswordRequest, ForgotPasswordRequest
from utils.logger import get_logger

logger = get_logger("backend.api.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

# ------ Register User -----
@router.post("/register", response_model=TokenResponse)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Rate limit registration by email to prevent spam (5 attempts per hour per email hash)
    rate_limit(hash(user.email), limit=5, window=3600)
    
    logger.info(f"User registration attempt", extra={"email": user.email})
    
    # Check if user already exists
    result = await db.execute(select(User).filter(User.email == user.email))
    existing_user = result.scalar_one_or_none()
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
    await db.commit()
    await db.refresh(new_user)

    # Generate JWT token
    access_token = create_access_token(data={"sub": str(new_user.id)})

    logger.info(f"User registered successfully", extra={"user_id": new_user.id, "email": user.email})
    return TokenResponse(token=access_token)

# ------ Login User -----
@router.post("/login", response_model=TokenResponse)
async def login_user(user_credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    # Rate limit login attempts to prevent brute force (10 attempts per 5 minutes per email)
    rate_limit(hash(user_credentials.email), limit=10, window=300)
    
    logger.info(f"Login attempt", extra={"email": user_credentials.email})
    
    result = await db.execute(
        select(User).filter(User.email == user_credentials.email)
    )
    db_user = result.scalar_one_or_none()

    if not db_user or not verify_password(user_credentials.password, db_user.password_hash):
        logger.warning(f"Login failed - invalid credentials", extra={"email": user_credentials.email})
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": str(db_user.id)})

    logger.info(f"Login successful", extra={"user_id": db_user.id, "email": user_credentials.email})
    return TokenResponse(token=access_token)

# ------ Passoword Reset ----- 
@router.post("/reset-password", response_model=TokenResponse)
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    logger.info("Password reset attempt", extra={"token": request.token})

    user_id = decode_access_token(request.token)
    if not user_id:
        logger.warning("Password reset failed - invalid token", extra={})
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    result = await db.execute(select(User).filter(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("Password reset failed - user not found", extra={"user_id": user_id})
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(request.new_password)
    await db.commit()
    logger.info("Password reset successful", extra={"user_id": user.id})
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(token=access_token)

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    logger.info("Forgot password request", extra={"email": request.email})
    result = await db.execute(select(User).filter(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("Forgot password failed - user not found", extra={"email": request.email})
        raise HTTPException(status_code=404, detail="User not found")
    
    reset_token = create_access_token(data={"sub": str(user.id)})

    # Here you would send the reset_token to the user's email.
    logger.info("Password reset token generated", extra={"user_id": user.id})
    return {"message": "Password reset instructions sent to your email."}
    
@router.get("/reset-password/{token}")
def verify_reset_token(token: str):
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return {"message": "Token is valid", "user_id": user_id}
   