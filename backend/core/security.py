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
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme (reads Authorization: Bearer <token> header)
oauth_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ------ Password Hashing -----
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

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


