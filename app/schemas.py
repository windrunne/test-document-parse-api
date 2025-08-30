from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    patient_first_name: str = Field(..., min_length=1, max_length=100)
    patient_last_name: str = Field(..., min_length=1, max_length=100)
    patient_dob: str = Field(..., min_length=1, max_length=20)
    order_type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    quantity: int = Field(1, ge=1)
    unit_price: float = Field(0.0, ge=0.0)
    total_amount: float = Field(0.0, ge=0.0)


class OrderCreate(OrderBase):
    status: Optional[str] = Field("pending", description="Order status")


class OrderUpdate(BaseModel):
    patient_first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    patient_last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    patient_dob: Optional[str] = Field(None, min_length=1, max_length=20)
    status: Optional[str] = None
    order_type: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=1)
    unit_price: Optional[float] = Field(None, ge=0.0)
    total_amount: Optional[float] = Field(None, ge=0.0)


class Order(OrderBase):
    id: int
    order_number: str
    status: str
    document_id: Optional[int] = None
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    original_filename: str
    content_type: str


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    patient_first_name: Optional[str] = None
    patient_last_name: Optional[str] = None
    patient_dob: Optional[str] = None
    extraction_status: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None


class Document(DocumentBase):
    id: int
    filename: str
    file_size: int
    s3_key: str
    s3_url: str
    patient_first_name: Optional[str] = None
    patient_last_name: Optional[str] = None
    patient_dob: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    extraction_status: str
    extraction_error: Optional[str] = None
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserActivityBase(BaseModel):
    user_id: int
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class UserActivityCreate(UserActivityBase):
    pass


class UserActivity(UserActivityBase):
    id: int
    user_id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class DocumentExtractionRequest(BaseModel):
    document_id: int


class DocumentExtractionResponse(BaseModel):
    success: bool
    extracted_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    type: Optional[str] = None
    value: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: dict = Field(
        ...,
        description="Error information",
        example={
            "code": "AUTH_001",
            "message": "Invalid credentials. Please check your username and password.",
            "details": {
                "field": "password",
                "value": "***",
                "rule": "valid password format"
            },
            "timestamp": "2025-01-27T10:30:00Z",
            "request_id": "req_12345"
        }
    )


class ValidationErrorResponse(BaseModel):
    error: dict = Field(
        ...,
        description="Validation error information",
        example={
            "code": "VALID_003",
            "message": "Validation failed. Please check your input.",
            "details": {
                "field_errors": [
                    {
                        "field": "email",
                        "message": "value is not a valid email",
                        "type": "value_error.email",
                        "value": "invalid-email"
                    }
                ],
                "total_errors": 1
            },
            "timestamp": "2025-01-27T10:30:00Z",
            "request_id": "req_12345"
        }
    )


class RateLimitResponse(BaseModel):
    error: dict = Field(
        ...,
        description="Rate limit information",
        example={
            "code": "RATE_001",
            "message": "Too many requests. Please wait 5 seconds before trying again.",
            "details": {
                "limit_type": "extraction",
                "retry_after": 5
            },
            "timestamp": "2025-01-27T10:30:00Z",
            "request_id": "req_12345"
        }
    )
