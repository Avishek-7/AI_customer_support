from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import hash_password, verify_password, create_access_token
from models.user import User
from schemas.user_schema import UserCreate, UserLogin, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# ------ Register User -----
@router.post("/register", response_model=TokenResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
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

    return TokenResponse(token=access_token)

# ------ Login User -----
@router.post("/login", response_model=TokenResponse)
def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    db_user = (
        db.query(User).filter(User.email == user_credentials.email).first()
    )

    if not db_user or not verify_password(user_credentials.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": str(db_user.id)})

    return TokenResponse(token=access_token)

    

