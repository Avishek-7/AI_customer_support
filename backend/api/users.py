from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import time

from core.database import get_db
from core.security import get_current_user, hash_password
from core.roles import require_admin
from core.error_handler import ErrorHandler
from models.user import User
from utils.logger import get_logger
from schemas.user_schema import (
    UserResponse,
    UserCreateAdmin,
    UserUpdate,
    UserListResponse,
)

logger = get_logger("backend.api.users")

router = APIRouter(prefix="/users", tags=["users"]) 


# Helper for access control
def ensure_self_or_admin(current_user: User, target_user_id: int):
    if current_user.role != "admin" and current_user.id != target_user_id:
        logger.warning(f"Unauthorized access attempt", extra={
            "user_id": current_user.id,
            "target_user_id": target_user_id,
            "role": current_user.role
        })
        raise ErrorHandler.forbidden("You do not have permission to access this resource")


# ----------------------------- Endpoints -----------------------------

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    logger.info("Fetching current user profile", extra={"user_id": current_user.id})
    return current_user


@router.get("/", response_model=UserListResponse, dependencies=[Depends(require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    logger.info("Listing users (admin)")
    result = await db.execute(select(User).order_by(User.id.asc()))
    users = result.scalars().all()
    return UserListResponse(users=users)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    start_time = time.time()
    ensure_self_or_admin(current_user, user_id)
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"User not found", extra={"user_id": user_id})
        raise ErrorHandler.not_found("User not found")
    latency = time.time() - start_time
    logger.info("User fetched", extra={"requested_id": user_id, "by_user": current_user.id, "latency": f"{latency:.3f}s"})
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_user(body: UserCreateAdmin, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    logger.info("Admin creating user", extra={"email": body.email})

    # Ensure email uniqueness
    result = await db.execute(select(User).filter(User.email == body.email))
    existing = result.scalar_one_or_none()
    if existing:
        logger.warning(f"User creation failed - email exists", extra={"email": body.email})
        raise ErrorHandler.conflict("Email already registered")

    try:
        new_user = User(
            email=body.email,
            name=body.name,
            password_hash=hash_password(body.password),
            role=body.role if body.role in ("user", "admin") else "user",
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        latency = time.time() - start_time
        logger.info("User created by admin", extra={"user_id": new_user.id, "email": new_user.email, "latency": f"{latency:.3f}s"})
        return new_user
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create user", extra={"email": body.email, "error": str(e)})
        raise ErrorHandler.internal_error("Failed to create user")


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, body: UserUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    start_time = time.time()
    ensure_self_or_admin(current_user, user_id)
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ErrorHandler.not_found("User not found")

    # Email update: ensure uniqueness
    if body.email and body.email != user.email:
        email_check = await db.execute(select(User).filter(User.email == body.email))
        if email_check.scalar_one_or_none():
            logger.warning(f"Email update failed - email already exists", extra={"email": body.email})
            raise ErrorHandler.conflict("Email already in use")
        user.email = body.email

    if body.name is not None:
        user.name = body.name

    if body.password:
        user.password_hash = hash_password(body.password)

    if body.role is not None:
        # Only admin can change role
        if current_user.role != "admin":
            logger.warning(f"Unauthorized role change attempt", extra={"user_id": current_user.id, "target_id": user_id})
            raise ErrorHandler.forbidden("Only admin can change role")
        if body.role not in ("user", "admin"):
            raise ErrorHandler.bad_request("Invalid role")
        user.role = body.role

    try:
        await db.commit()
        await db.refresh(user)
        
        latency = time.time() - start_time
        logger.info("User updated", extra={"user_id": user.id, "by_user": current_user.id, "latency": f"{latency:.3f}s"})
        return user
    except Exception as e:
        await db.rollback()
        logger.error("Failed to update user", extra={"user_id": user_id, "error": str(e)})
        raise ErrorHandler.internal_error("Failed to update user")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"User not found for deletion", extra={"user_id": user_id})
        raise ErrorHandler.not_found("User not found")
    
    try:
        await db.delete(user)
        await db.commit()
        latency = time.time() - start_time
        logger.info("User deleted by admin", extra={"user_id": user_id, "latency": f"{latency:.3f}s"})
    except Exception as e:
        await db.rollback()
        logger.error("Failed to delete user", extra={"user_id": user_id, "error": str(e)})
        raise ErrorHandler.internal_error("Failed to delete user")
    return None
