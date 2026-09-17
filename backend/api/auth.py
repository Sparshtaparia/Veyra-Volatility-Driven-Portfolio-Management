from datetime import datetime, timedelta
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import hashlib

from backend.dependencies.db import get_db
from config.settings import get_settings
from database.models import UserModel
from backend.services.brevo_client import BrevoClient

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

class SignUpRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

def get_password_hash(password: str) -> str:
    # A simple hash for now (in production, use bcrypt or passlib)
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignUpRequest, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(UserModel).filter(UserModel.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = UserModel(
        name=request.name,
        email=request.email,
        password_hash=get_password_hash(request.password),
        role="INVESTOR",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send welcome email via Brevo
    brevo = BrevoClient()
    await brevo.send_welcome_email(user.email, user.name)

    # Generate token
    access_token_expires = timedelta(minutes=settings.jwt_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "user_metadata": {"role": user.role, "full_name": user.name}},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.jwt_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "user_metadata": {"role": user.role, "full_name": user.name}},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
