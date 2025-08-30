from fastapi import HTTPException, status
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class BaseAPIException(HTTPException):
    """Base exception class for all API errors"""
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        self.error_code = error_code
        self.details = details or {}
        self.user_message = user_message or message
        
        super().__init__(status_code=status_code, detail={
            "error_code": error_code,
            "message": message,
            "user_message": user_message,
            "details": details
        })


class AuthenticationError(BaseAPIException):
    """Authentication failed"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_001",
            message=message,
            details=details,
            user_message="Invalid credentials. Please check your username and password."
        )


class TokenExpiredError(BaseAPIException):
    """JWT token has expired"""
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_002",
            message="JWT token has expired",
            details=details,
            user_message="Your session has expired. Please log in again."
        )


class TokenInvalidError(BaseAPIException):
    """JWT token is invalid"""
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_003",
            message="JWT token is invalid",
            details=details,
            user_message="Invalid session token. Please log in again."
        )


class InsufficientPermissionsError(BaseAPIException):
    """User doesn't have sufficient permissions"""
    
    def __init__(self, required_permission: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTH_004",
            message=f"Insufficient permissions. Required: {required_permission}",
            details=details,
            user_message="You don't have permission to perform this action."
        )


class UserNotFoundError(BaseAPIException):
    """User not found"""
    
    def __init__(self, user_id: Optional[int] = None, username: Optional[str] = None):
        details = {}
        if user_id:
            details["user_id"] = user_id
        if username:
            details["username"] = username
            
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="AUTH_005",
            message="User not found",
            details=details,
            user_message="User account not found."
        )


class UserAlreadyExistsError(BaseAPIException):
    """User already exists"""
    
    def __init__(self, username: str, email: Optional[str] = None):
        details = {"username": username}
        if email:
            details["email"] = email
            
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="AUTH_006",
            message=f"User with username '{username}' already exists",
            details=details,
            user_message="A user with this username already exists. Please choose a different username."
        )


class InvalidCredentialsError(BaseAPIException):
    """Invalid login credentials"""
    
    def __init__(self, username: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["username"] = username
        
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_007",
            message=f"Invalid credentials for user '{username}'",
            details=details,
            user_message="Invalid username or password. Please try again."
        )


class AccountLockedError(BaseAPIException):
    """User account is locked"""
    
    def __init__(self, username: str, reason: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "username": username,
            "reason": reason
        })
        
        super().__init__(
            status_code=status.HTTP_423_LOCKED,
            error_code="AUTH_008",
            message=f"Account locked for user '{username}'. Reason: {reason}",
            details=details,
            user_message="Your account has been locked. Please contact support for assistance."
        )


class ValidationError(BaseAPIException):
    """Data validation failed"""
    
    def __init__(self, field: str, value: Any, rule: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "field": field,
            "value": value,
            "rule": rule
        })
        
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALID_001",
            message=f"Validation failed for field '{field}'. Rule: {rule}",
            details=details,
            user_message=f"Invalid {field}. Please check your input and try again."
        )


class RequiredFieldError(BaseAPIException):
    """Required field is missing"""
    
    def __init__(self, field: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["field"] = field
        
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALID_002",
            message=f"Required field '{field}' is missing",
            details=details,
            user_message=f"{field} is required. Please fill in this field."
        )


class ResourceNotFoundError(BaseAPIException):
    """Resource not found"""
    
    def __init__(self, resource_type: str, resource_id: Any, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "resource_type": resource_type,
            "resource_id": resource_id
        })
        
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_001",
            message=f"{resource_type} with ID {resource_id} not found",
            details=details,
            user_message=f"{resource_type} not found."
        )


class ResourceAlreadyExistsError(BaseAPIException):
    """Resource already exists"""
    
    def __init__(self, resource_type: str, identifier: str, value: Any, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "resource_type": resource_type,
            "identifier": identifier,
            "value": value
        })
        
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_002",
            message=f"{resource_type} with {identifier} '{value}' already exists",
            details=details,
            user_message=f"A {resource_type.lower()} with this {identifier} already exists."
        )


class ResourceAccessDeniedError(BaseAPIException):
    """Access to resource denied"""
    
    def __init__(self, resource_type: str, resource_id: Any, user_id: int, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id
        })
        
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="RESOURCE_003",
            message=f"Access denied to {resource_type} {resource_id} for user {user_id}",
            details=details,
            user_message="You don't have permission to access this resource."
        )


class ExternalServiceError(BaseAPIException):
    """External service error"""
    
    def __init__(self, service_name: str, operation: str, error: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "service_name": service_name,
            "operation": operation,
            "error": error
        })
        
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_001",
            message=f"External service '{service_name}' error during {operation}: {error}",
            details=details,
            user_message="Service temporarily unavailable. Please try again later."
        )


class OpenAIServiceError(BaseAPIException):
    """OpenAI service error"""
    
    def __init__(self, operation: str, error: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "service_name": "OpenAI",
            "operation": operation,
            "error": error
        })
        
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="OPENAI_001",
            message=f"OpenAI service error during {operation}: {error}",
            details=details,
            user_message="AI processing service is temporarily unavailable. Please try again later."
        )


class S3ServiceError(BaseAPIException):
    """AWS S3 service error"""
    
    def __init__(self, operation: str, error: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "service_name": "AWS S3",
            "operation": operation,
            "error": error
        })
        
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="S3_001",
            message=f"S3 service error during {operation}: {error}",
            details=details,
            user_message="File storage service is temporarily unavailable. Please try again later."
        )


class RateLimitExceededError(BaseAPIException):
    """Rate limit exceeded"""
    
    def __init__(self, limit_type: str, retry_after: int, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "limit_type": limit_type,
            "retry_after": retry_after
        })
        
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_001",
            message=f"Rate limit exceeded for {limit_type}",
            details=details,
            user_message=f"Too many requests. Please wait {retry_after} seconds before trying again."
        )


class DatabaseError(BaseAPIException):
    """Database operation failed"""
    
    def __init__(self, operation: str, table: str, error: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "operation": operation,
            "table": table,
            "error": error
        })
        
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DB_001",
            message=f"Database error during {operation} on {table}: {error}",
            details=details,
            user_message="Database operation failed. Please try again later."
        )


class DatabaseConnectionError(BaseAPIException):
    """Database connection failed"""
    
    def __init__(self, error: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["error"] = error
        
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="DB_002",
            message=f"Database connection failed: {error}",
            details=details,
            user_message="Database connection failed. Please try again later."
        )


class FileProcessingError(BaseAPIException):
    """File processing failed"""
    
    def __init__(self, filename: str, operation: str, error: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "filename": filename,
            "operation": operation,
            "error": error
        })
        
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="FILE_001",
            message=f"File processing failed for '{filename}' during {operation}: {error}",
            details=details,
            user_message="File processing failed. Please check your file and try again."
        )


class FileTooLargeError(BaseAPIException):
    """File is too large"""
    
    def __init__(self, filename: str, file_size: int, max_size: int, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "filename": filename,
            "file_size": file_size,
            "max_size": max_size
        })
        
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_code="FILE_002",
            message=f"File '{filename}' is too large. Size: {file_size}, Max: {max_size}",
            details=details,
            user_message=f"File is too large. Maximum size allowed is {max_size} bytes."
        )


class UnsupportedFileTypeError(BaseAPIException):
    """Unsupported file type"""
    
    def __init__(self, filename: str, file_type: str, supported_types: List[str], details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details.update({
            "filename": filename,
            "file_type": file_type,
            "supported_types": supported_types
        })
        
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error_code="FILE_003",
            message=f"Unsupported file type '{file_type}' for '{filename}'. Supported: {supported_types}",
            details=details,
            user_message=f"File type not supported. Supported types: {', '.join(supported_types)}"
        )


def log_exception_with_context(
    exception: Exception,
    context: Dict[str, Any],
    user_id: Optional[int] = None,
    request_id: Optional[str] = None
):
    """Log exception with additional context for debugging"""
    
    log_data = {
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        "context": context
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    if request_id:
        log_data["request_id"] = request_id
    
    logger.error(f"Exception occurred: {log_data}")
    
    import traceback
    logger.error(f"Full traceback: {traceback.format_exc()}")
