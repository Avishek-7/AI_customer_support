from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"


# -------- Users CRUD Schemas --------
class UserResponse(BaseModel):
    id: int
    name: Optional[str] = None
    email: EmailStr
    role: str

    class Config:
        from_attributes = True


class UserCreateAdmin(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    role: Optional[str] = "user"  # Only applied if admin creates


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None  # Admin-only


class UserListResponse(BaseModel):
    users: List[UserResponse]

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters") 
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain an uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain a number")
        return v
class ResetTokenParams(BaseModel):
    token: str



