from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from src.core.config import settings
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Check if it's a Django pbkdf2_sha256 hash. If we want compatibility,
        # we might need passlib.hash.django_pbkdf2_sha256, but for now we define bcrypt.
        if hashed_password.startswith("pbkdf2_sha256$"):
            from passlib.hash import django_pbkdf2_sha256
            return django_pbkdf2_sha256.verify(plain_password, hashed_password)
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
