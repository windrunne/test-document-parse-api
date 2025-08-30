from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from jose import JWTError, ExpiredSignatureError
import logging
from typing import Union, Dict, Any
from .exceptions import (
    BaseAPIException,
    log_exception_with_context,
    DatabaseError,
    DatabaseConnectionError,
    ExternalServiceError,
    OpenAIServiceError,
    S3ServiceError,
    RateLimitExceededError,
    ValidationError,
    RequiredFieldError
)

logger = logging.getLogger(__name__)


async def base_api_exception_handler(request: Request, exc: BaseAPIException):
    """Handle all custom API exceptions"""
    
    context = {
        "path": request.url.path,
        "method": request.method,
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
        "client_ip": request.client.host if request.client else None
    }
    
    log_exception_with_context(
        exception=exc,
        context=context,
        user_id=getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None,
        request_id=getattr(request.state, 'request_id', None) if hasattr(request.state, 'request_id') else None
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.user_message,
                "details": exc.details,
                "timestamp": exc.details.get("timestamp"),
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    
    field_errors = []
    for error in exc.errors():
        field_name = " -> ".join(str(loc) for loc in error["loc"])
        field_errors.append({
            "field": field_name,
            "message": error["msg"],
            "type": error["type"],
            "value": error.get("input")
        })
    
    context = {
        "path": request.url.path,
        "method": request.method,
        "field_errors": field_errors
    }
    
    log_exception_with_context(
        exception=exc,
        context=context,
        user_id=getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None,
        request_id=getattr(request.state, 'request_id', None) if hasattr(request.state, 'request_id') else None
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALID_003",
                "message": "Validation failed. Please check your input.",
                "details": {
                    "field_errors": field_errors,
                    "total_errors": len(field_errors)
                },
                "timestamp": None,
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )


async def jwt_exception_handler(request: Request, exc: JWTError):
    """Handle JWT-related errors"""

    error_code = "AUTH_009"
    user_message = "Invalid authentication token."

    if isinstance(exc, ExpiredSignatureError):
        error_code = "AUTH_002"
        user_message = "Your session has expired. Please log in again."
    elif "claims" in str(exc).lower() or "invalid" in str(exc).lower():
        error_code = "AUTH_003"
        user_message = "Invalid authentication token. Please log in again."
    
    context = {
        "path": request.url.path,
        "method": request.method,
        "jwt_error_type": type(exc).__name__
    }
    
    log_exception_with_context(
        exception=exc,
        context=context,
        user_id=getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None,
        request_id=getattr(request.state, 'request_id', None) if hasattr(request.state, 'request_id') else None
    )
    
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": {
                "code": error_code,
                "message": user_message,
                "details": {
                    "jwt_error_type": type(exc).__name__,
                    "jwt_error_message": str(exc)
                },
                "timestamp": None,
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle SQLAlchemy database errors"""
    
    error_code = "DB_001"
    user_message = "Database operation failed. Please try again later."
    
    if isinstance(exc, IntegrityError):
        error_code = "DB_003"
        user_message = "Data integrity error. The operation cannot be completed."
    elif isinstance(exc, OperationalError):
        error_code = "DB_004"
        user_message = "Database connection error. Please try again later."
    
    context = {
        "path": request.url.path,
        "method": request.method,
        "db_error_type": type(exc).__name__,
        "db_error_code": getattr(exc, 'code', None)
    }
    
    log_exception_with_context(
        exception=exc,
        context=context,
        user_id=getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None,
        request_id=getattr(request.state, 'request_id', None) if hasattr(request.state, 'request_id') else None
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": error_code,
                "message": user_message,
                "details": {
                    "db_error_type": type(exc).__name__,
                    "db_error_message": str(exc)
                },
                "timestamp": None,
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )


async def openai_exception_handler(request: Request, exc: Exception):
    """Handle OpenAI service errors"""
    
    error_message = str(exc)
    if "openai" in error_message.lower() or "api" in error_message.lower():
        error_code = "OPENAI_001"
        user_message = "AI processing service is temporarily unavailable. Please try again later."
    else:
        error_code = "EXTERNAL_001"
        user_message = "External service error. Please try again later."
    
    context = {
        "path": request.url.path,
        "method": request.method,
        "service": "OpenAI",
        "error_type": type(exc).__name__
    }
    
    log_exception_with_context(
        exception=exc,
        context=context,
        user_id=getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None,
        request_id=getattr(request.state, 'request_id', None) if hasattr(request.state, 'request_id') else None
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": error_code,
                "message": user_message,
                "details": {
                    "service": "OpenAI",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)
                },
                "timestamp": None,
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )


async def s3_exception_handler(request: Request, exc: Exception):
    """Handle AWS S3 service errors"""
    
    error_code = "S3_001"
    user_message = "File storage service is temporarily unavailable. Please try again later."
    
    context = {
        "path": request.url.path,
        "method": request.method,
        "service": "AWS S3",
        "error_type": type(exc).__name__
    }
    
    log_exception_with_context(
        exception=exc,
        context=context,
        user_id=getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None,
        request_id=getattr(request.state, 'request_id', None) if hasattr(request.state, 'request_id') else None
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": error_code,
                "message": user_message,
                "details": {
                    "service": "AWS S3",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)
                },
                "timestamp": None,
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all other unhandled exceptions"""
    
    context = {
        "path": request.url.path,
        "method": request.method,
        "error_type": type(exc).__name__,
        "unhandled": True
    }
    
    log_exception_with_context(
        exception=exc,
        context=context,
        user_id=getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None,
        request_id=getattr(request.state, 'request_id', None) if hasattr(request.state, 'request_id') else None
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_001",
                "message": "An unexpected error occurred. Please try again later.",
                "details": {
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)
                },
                "timestamp": None,
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app"""
    
    app.add_exception_handler(BaseAPIException, base_api_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(JWTError, jwt_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("✅ Exception handlers registered successfully")


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Dict[str, Any] = None,
    user_message: str = None
) -> JSONResponse:
    """Utility function to create consistent error responses"""
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": user_message or message,
                "details": details or {},
                "timestamp": None,
                "request_id": None
            }
        }
    )
