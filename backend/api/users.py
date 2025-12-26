from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from core.security import get_current_user, hash_password
from core.roles import require_admin
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


# ------------------------ Helper permissions ------------------------
def ensure_self_or_admin(current_user: User, target_user_id: int):
    if current_user.role != "admin" and current_user.id != target_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# ----------------------------- Endpoints -----------------------------

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    logger.info("Fetching current user profile", extra={"user_id": current_user.id})
    return current_user


@router.get("/", response_model=UserListResponse, dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)):
    logger.info("Listing users (admin)")
    users = db.query(User).order_by(User.id.asc()).all()
    return UserListResponse(users=users)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_self_or_admin(current_user, user_id)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info("Fetched user", extra={"requested_id": user_id, "by_user": current_user.id})
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_user(body: UserCreateAdmin, db: Session = Depends(get_db)):
    logger.info("Admin creating user", extra={"email": body.email})

    # Ensure email uniqueness
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        role=body.role if body.role in ("user", "admin") else "user",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info("User created by admin", extra={"user_id": new_user.id})
    return new_user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_self_or_admin(current_user, user_id)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Email update: ensure uniqueness
    if body.email and body.email != user.email:
        if db.query(User).filter(User.email == body.email).first():
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = body.email

    if body.name is not None:
        user.name = body.name

    if body.password:
        user.password_hash = hash_password(body.password)

    if body.role is not None:
        # Only admin can change role
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Only admin can change role")
        if body.role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = body.role

    db.commit()
    db.refresh(user)
    logger.info("User updated", extra={"user_id": user.id, "by_user": current_user.id})
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    logger.info("User deleted", extra={"user_id": user_id})
    return None
