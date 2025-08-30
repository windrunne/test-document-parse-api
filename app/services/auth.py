from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from fastapi import HTTPException, status
from app.config import settings
from app.schemas import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except UnknownHashError:
        # Handle case where hash format is not recognized
        return False
    except Exception as e:
        # Log any other password verification errors
        return False


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
        return token_data
    except JWTError:
        return None


def authenticate_user(username: str, password: str, user) -> bool:
    """Authenticate a user with username and password"""
    if not user:
        return False
    
    try:
        if not verify_password(password, user.hashed_password):
            return False
        return True
    except Exception as e:
        # Log the error but don't expose it to the user
        return False
