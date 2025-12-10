from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from core.database import get_db
from models.user import User
from core.config import settings

# Password hashing
import bcrypt

# OAuth2 scheme (reads Authorization: Bearer <token> header)
oauth_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ------ Password Hashing -----
def hash_password(password: str) -> str:
    """Hash password using bcrypt. Safely handles 72-byte limit.
    
    Returns hashed password as string.
    """
    # Ensure password is a string
    if not isinstance(password, str):
        password = str(password)
    
    # Convert to bytes and truncate to 72 bytes
    password_bytes = password.encode('utf-8')[:72]
    
    if not password_bytes:
        raise ValueError("Password cannot be empty")
    
    # Hash with bcrypt (rounds=12 is the default)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string for database storage
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    # Ensure plain_password is a string
    if not isinstance(plain_password, str):
        plain_password = str(plain_password)
    
    # Truncate to 72 bytes like hash_password does
    password_bytes = plain_password.encode('utf-8')[:72]
    
    if not password_bytes:
        return False
    
    # Ensure hashed_password is bytes
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    
    try:
        return bcrypt.checkpw(password_bytes, hashed_password)
    except Exception:
        return False

# ------ JWT Token creation -----
def create_access_token(data: dict) -> str:
    """Crate a JWT access token with expiry."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
def decode_access_token(token: str) -> Optional[str]:
    """
    Decode token and return the user_id (stored in 'sub'),
    or None if invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None
    
# ------ Get Current User -----
def get_current_user(token: str = Depends(oauth_scheme), db: Session = Depends(get_db)) -> User:
    """
    Dependency used in protected routes.
    - Reads JWT from Authorization header.
    - Decodes it.
    - Loads the User from DB.
    - Raises 401 if anything is invalid.
    """
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_access_token(token)
    if user_id is None:
        raise credential_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credential_exception
    
    return user


