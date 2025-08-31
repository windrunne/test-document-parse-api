from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, User as UserSchema, Token
from app.services.auth import get_password_hash, create_access_token, authenticate_user
from app.services.activity_logger import activity_logger
from app.api.deps import get_current_user
from app.core.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidCredentialsError,
    AccountLockedError,
    DatabaseError,
    DatabaseConnectionError,
    ValidationError,
    RequiredFieldError
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserSchema)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    request: Request = None
):
    """Register a new user"""
    
    if not user_data.username or not user_data.username.strip():
        raise RequiredFieldError("username")
    
    if not user_data.email or not user_data.email.strip():
        raise RequiredFieldError("email")
    
    if not user_data.password or len(user_data.password) < 6:
        raise ValidationError("password", "***", "minimum 6 characters")
    
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, user_data.email):
        raise ValidationError("email", user_data.email, "valid email format")
    
    username_pattern = r'^[a-zA-Z0-9_]+$'
    if not re.match(username_pattern, user_data.username):
        raise ValidationError("username", user_data.username, "alphanumeric characters and underscores only")
    
    try:
        existing_user = db.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()
        
        if existing_user:
            if existing_user.email == user_data.email:
                raise UserAlreadyExistsError(
                    username=user_data.username,
                    email=user_data.email
                )
            else:
                raise UserAlreadyExistsError(username=user_data.username)
        
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        if request:
            await activity_logger.log_activity(
                db=db,
                user_id=db_user.id,
                action="register",
                resource_type="user",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
        
        return UserSchema.from_orm(db_user)
        
    except (UserAlreadyExistsError, ValidationError, RequiredFieldError):
        raise
        
    except IntegrityError as e:
        db.rollback()
        
        error_msg = str(e).lower()
        if "unique constraint" in error_msg:
            if "email" in error_msg:
                raise UserAlreadyExistsError(
                    username=user_data.username,
                    email=user_data.email
                )
            elif "username" in error_msg:
                raise UserAlreadyExistsError(username=user_data.username)
            else:
                raise UserAlreadyExistsError(username=user_data.username)
        else:
            raise DatabaseError(
                operation="user creation",
                table="users",
                error=str(e)
            )
        
    except OperationalError as e:
        db.rollback()
        raise DatabaseConnectionError(str(e))
        
    except Exception as e:
        db.rollback()
        import traceback
        
        if "password" in str(e).lower():
            raise ValidationError("password", "***", "valid password format")
        elif "email" in str(e).lower():
            raise ValidationError("email", user_data.email, "valid email format")
        else:
            raise DatabaseError(
                operation="user creation",
                table="users",
                error=str(e)
            )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Login user and return access token"""
    
    if not form_data.username or not form_data.username.strip():
        raise RequiredFieldError("username")
    
    if not form_data.password:
        raise RequiredFieldError("password")
    
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        
        if not user:
            raise InvalidCredentialsError(form_data.username)
        
        if not authenticate_user(form_data.username, form_data.password, user):
            raise InvalidCredentialsError(form_data.username)
        
        if not user.is_active:
            raise AccountLockedError(
                username=form_data.username,
                reason="Account is inactive"
            )
        
        failed_attempts = getattr(user, 'failed_login_attempts', 0)
        if failed_attempts >= 5:  # Lock after 5 failed attempts
            raise AccountLockedError(
                username=form_data.username,
                reason="Too many failed login attempts"
            )
        
        access_token = create_access_token(data={"sub": user.username})
        
        if hasattr(user, 'failed_login_attempts') and user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            db.commit()
        
        if request:
            await activity_logger.log_login(
                db=db,
                user_id=user.id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except (InvalidCredentialsError, AccountLockedError):
        raise
        
    except OperationalError as e:
        raise DatabaseConnectionError(str(e))
        
    except Exception as e:
        import traceback
        
        if "password" in str(e).lower():
            raise InvalidCredentialsError(form_data.username)
        elif "database" in str(e).lower():
            raise DatabaseConnectionError(str(e))
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login service temporarily unavailable. Please try again later."
            )


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    try:
        return UserSchema.from_orm(current_user)
        
    except Exception as e:
        import traceback
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )



