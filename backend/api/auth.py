from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.security import hash_password, verify_password, create_access_token, decode_access_token
from core.rate_limit import rate_limit
from core.error_handler import ErrorHandler
from models.user import User
from schemas.user_schema import UserCreate, UserLogin, TokenResponse, ResetPasswordRequest, ForgotPasswordRequest
from utils.logger import get_logger
from utils.email import send_reset_email
import time

logger = get_logger("backend.api.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

# ------ Register User -----
@router.post("/register", response_model=TokenResponse)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    
    # Rate limit registration by email to prevent spam (5 attempts per hour per email hash)
    rate_limit(hash(user.email), limit=5, window=3600)
    
    logger.info(f"User registration attempt", extra={"email": user.email})
    
    # Check if user already exists
    result = await db.execute(select(User).filter(User.email == user.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        logger.warning(f"Registration failed - email exists", extra={"email": user.email})
        raise ErrorHandler.conflict("Email already registered")
    
    # Hash password
    hashed_pw = hash_password(user.password)

    new_user = User(
        name=user.full_name,
        email=user.email,
        password_hash=hashed_pw
    )
    
    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Generate JWT token
        access_token = create_access_token(data={"sub": str(new_user.id)})

        latency = time.time() - start_time
        logger.info(f"User registered successfully", extra={
            "user_id": new_user.id,
            "email": user.email,
            "latency": f"{latency:.3f}s"
        })
        return TokenResponse(token=access_token)
    except Exception as e:
        await db.rollback()
        logger.error(f"Registration failed", extra={"email": user.email, "error": str(e)})
        raise ErrorHandler.internal_error("Failed to register user")

# ------ Login User -----
@router.post("/login", response_model=TokenResponse)
async def login_user(user_credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    
    # Rate limit login attempts to prevent brute force (10 attempts per 5 minutes per email)
    rate_limit(hash(user_credentials.email), limit=10, window=300)
    
    logger.info(f"Login attempt", extra={"email": user_credentials.email})
    
    result = await db.execute(
        select(User).filter(User.email == user_credentials.email)
    )
    db_user = result.scalar_one_or_none()

    if not db_user or not verify_password(user_credentials.password, db_user.password_hash):
        logger.warning(f"Login failed - invalid credentials", extra={"email": user_credentials.email})
        raise ErrorHandler.unauthorized("Invalid email or password")
    
    access_token = create_access_token(data={"sub": str(db_user.id)})

    latency = time.time() - start_time
    logger.info(f"Login successful", extra={
        "user_id": db_user.id,
        "email": user_credentials.email,
        "latency": f"{latency:.3f}s"
    })
    return TokenResponse(token=access_token)

# ------ Password Reset ----- 
@router.post("/reset-password", response_model=TokenResponse)
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    logger.info("Password reset attempt")
    user_id = decode_access_token(request.token)
    if not user_id:
        logger.warning("Password reset failed - invalid token")
        raise ErrorHandler.bad_request("Invalid or expired token")
    result = await db.execute(select(User).filter(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("Password reset failed - user not found", extra={"user_id": user_id})
        raise ErrorHandler.not_found("User not found")
    try:
        user.password_hash = hash_password(request.new_password)
        await db.commit()
        access_token = create_access_token(data={"sub": str(user.id)})
        latency = time.time() - start_time
        logger.info("Password reset successful", extra={"user_id": user.id, "latency": f"{latency:.3f}s"})
        return TokenResponse(token=access_token)
    except Exception as e:
        await db.rollback()
        logger.error("Password reset failed", extra={"user_id": user.id, "error": str(e)})
        raise ErrorHandler.internal_error("Failed to reset password")

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    logger.info("Forgot password request", extra={"email": request.email})
    result = await db.execute(select(User).filter(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("Forgot password failed - user not found", extra={"email": request.email})
        # Don't reveal if email exists (security best practice)
        return {"message": "If the email exists, a reset link has been sent"}
    
    reset_token = create_access_token(data={"sub": str(user.id)})
    
    # Send password reset email
    email_sent = send_reset_email(to=user.email, reset_token=reset_token)
    
    latency = time.time() - start_time
    if email_sent:
        logger.info("Password reset email sent", extra={"user_id": user.id, "email": user.email, "latency": f"{latency:.3f}s"})
    else:
        logger.warning("Failed to send password reset email", extra={"user_id": user.id, "email": user.email})
    
    return {"message": "If the email exists, a reset link has been sent"}
    
@router.get("/reset-password/{token}")
def verify_reset_token(token: str):
    user_id = decode_access_token(token)
    if not user_id:
        raise ErrorHandler.bad_request("Invalid or expired token")
    logger.info("Reset token verified", extra={"user_id": user_id})
    return {"message": "Token is valid", "user_id": user_id}