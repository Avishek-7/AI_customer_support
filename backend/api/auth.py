import asyncio
import hashlib
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.config import settings
from core.security import hash_password, verify_password, create_access_token, decode_access_token
from core.rate_limit import rate_limit, rate_limit_key
from core.error_handler import ErrorHandler
from models.user import User
from schemas.user_schema import UserCreate, UserLogin, TokenResponse, ResetPasswordRequest, ForgotPasswordRequest
from utils.logger import get_logger
from utils.email import send_reset_email

logger = get_logger("backend.api.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


def _email_hash(email: str) -> str:
    normalized = email.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _client_ip(http_request: Request) -> str:
    forwarded_for = http_request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return http_request.client.host if http_request.client else "unknown"

# ------ Register User -----
@router.post("/register", response_model=TokenResponse)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    user_email_hash = _email_hash(user.email)
    
    # Rate limit registration by email to prevent spam (5 attempts per hour per email hash)
    rate_limit(user_email_hash, limit=5, window=3600)
    
    logger.info(f"User registration attempt", extra={"user_email_hash": user_email_hash})
    
    # Check if user already exists
    result = await db.execute(select(User).filter(User.email == user.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        logger.warning(f"Registration failed - email exists", extra={"user_email_hash": user_email_hash})
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
            "user_email_hash": user_email_hash,
            "latency": f"{latency:.3f}s"
        })
        return TokenResponse(token=access_token)
    except Exception as e:
        await db.rollback()
        logger.error(f"Registration failed", extra={"user_email_hash": user_email_hash, "error": str(e)})
        raise ErrorHandler.internal_error("Failed to register user")

# ------ Login User -----
@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_credentials: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    start_time = time.time()
    user_email_hash = _email_hash(user_credentials.email)
    
    # Rate limit login attempts to prevent brute force (10 attempts per 5 minutes per email)
    rate_limit(user_email_hash, limit=10, window=300)
    
    logger.info(f"Login attempt", extra={"user_email_hash": user_email_hash})
    
    result = await db.execute(
        select(User).filter(User.email == user_credentials.email)
    )
    db_user = result.scalar_one_or_none()

    if not db_user or not verify_password(user_credentials.password, db_user.password_hash):
        logger.warning(f"Login failed - invalid credentials", extra={"user_email_hash": user_email_hash})
        raise ErrorHandler.unauthorized("Invalid email or password")
    
    access_token = create_access_token(data={"sub": str(db_user.id)})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    latency = time.time() - start_time
    logger.info(f"Login successful", extra={
        "user_id": db_user.id,
        "user_email_hash": user_email_hash,
        "latency": f"{latency:.3f}s"
    })
    return TokenResponse(token=access_token)

# ------ Password Reset ----- 
@router.post("/reset-password", response_model=TokenResponse)
async def reset_password(request: ResetPasswordRequest, http_request: Request, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    client_ip = _client_ip(http_request)
    token_hash_prefix = hashlib.sha256(request.token.encode("utf-8")).hexdigest()[:12]

    try:
        rate_limit_key(key=f"reset_password:{client_ip}:{token_hash_prefix}", limit=10, window=3600)
    except HTTPException as exc:
        if exc.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail=exc.detail,
                headers={"Retry-After": "3600"},
            )
        raise

    logger.info("Password reset attempt")
    user_id = decode_access_token(request.token)
    if not user_id:
        logger.warning("Password reset failed - invalid token")
        raise ErrorHandler.bad_request("Invalid or expired token")

    try:
        parsed_user_id = int(user_id)
    except (TypeError, ValueError):
        logger.warning("Password reset failed - malformed token subject", extra={"user_id": user_id})
        raise ErrorHandler.bad_request("Invalid or expired token")

    result = await db.execute(select(User).filter(User.id == parsed_user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("Password reset failed - user not found", extra={"user_id": user_id})
        raise ErrorHandler.not_found("User not found")

    if not user.reset_token or user.reset_token != request.token or user.reset_token_used:
        logger.warning("Password reset failed - token already used or mismatched", extra={"user_id": user.id})
        raise ErrorHandler.bad_request("Invalid or expired token")

    try:
        user.password_hash = hash_password(request.new_password)
        user.reset_token_used = True
        user.reset_token = None
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
async def forgot_password(forgot_password_request: ForgotPasswordRequest, http_request: Request, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    user_email_hash = _email_hash(forgot_password_request.email)
    client_ip = _client_ip(http_request)

    rate_limit_key(key=f"forgot_password:{client_ip}", limit=5, window=3600)

    logger.info("Forgot password request", extra={"user_email_hash": user_email_hash, "client_ip": client_ip})
    result = await db.execute(select(User).filter(User.email == forgot_password_request.email))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("Forgot password failed - user not found", extra={"user_email_hash": user_email_hash, "client_ip": client_ip})
        # Don't reveal if email exists (security best practice)
        return {"message": "If the email exists, a reset link has been sent"}
    
    reset_token = create_access_token(data={"sub": str(user.id)})

    try:
        user.reset_token = reset_token
        user.reset_token_used = False
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Failed to persist reset token", extra={"user_id": user.id, "error": str(e)})
        raise ErrorHandler.internal_error("Failed to process forgot password request")
    
    # Send password reset email
    email_sent = await asyncio.to_thread(send_reset_email, to=user.email, reset_token=reset_token)
    
    latency = time.time() - start_time
    if email_sent:
        logger.info("Password reset email sent", extra={"user_id": user.id, "user_email_hash": user_email_hash, "latency": f"{latency:.3f}s"})
    else:
        logger.warning("Failed to send password reset email", extra={"user_id": user.id, "user_email_hash": user_email_hash})
    
    return {"message": "If the email exists, a reset link has been sent"}
    
@router.get("/reset-password/{token}")
async def verify_reset_token(token: str, db: AsyncSession = Depends(get_db)):
    user_id = decode_access_token(token)
    if not user_id:
        raise ErrorHandler.bad_request("Invalid or expired token")

    try:
        parsed_user_id = int(user_id)
    except (TypeError, ValueError):
        raise ErrorHandler.bad_request("Invalid or expired token")

    result = await db.execute(select(User).filter(User.id == parsed_user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ErrorHandler.not_found("User not found")

    if not user.reset_token or user.reset_token != token or user.reset_token_used:
        raise ErrorHandler.bad_request("Invalid or expired token")

    logger.info("Reset token verified", extra={"user_id": user_id})
    return {"message": "Token is valid", "user_id": user_id}