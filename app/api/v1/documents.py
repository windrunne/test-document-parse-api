from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from typing import List, Optional, Dict
from app.database import get_db
from app.models import Document, User
from app.schemas import Document as DocumentSchema, PaginatedResponse, DocumentExtractionResponse
from app.api.deps import get_current_active_user
from app.services.s3_service import s3_service
from app.services.openai_service import openai_service
from app.services.document_processor import document_processor
from app.services.activity_logger import activity_logger
from app.core.exceptions import (
    FileTooLargeError,
    UnsupportedFileTypeError,
    FileProcessingError,
    ResourceNotFoundError,
    ResourceAccessDeniedError,
    OpenAIServiceError,
    S3ServiceError,
    RateLimitExceededError,
    DatabaseError,
    DatabaseConnectionError,
    ValidationError,
    RequiredFieldError
)
import uuid
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

extraction_rate_limit: Dict[int, float] = {} 
RATE_LIMIT_SECONDS = 5

def cleanup_rate_limiter():
    """Clean up old rate limit entries to prevent memory leaks"""
    current_time = time.time()
    cutoff_time = current_time - 3600
    
    expired_users = [
        user_id for user_id, last_time in extraction_rate_limit.items() 
        if last_time < cutoff_time
    ]
    for user_id in expired_users:
        del extraction_rate_limit[user_id]
    
    if expired_users:
        logger.debug(f"Cleaned up {len(expired_users)} expired rate limit entries")


def generate_filename() -> str:
    """Generate unique filename"""
    return f"{uuid.uuid4().hex}"


@router.post("/upload", response_model=DocumentSchema)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Upload a document and extract patient data"""
    
    if not file.filename:
        raise RequiredFieldError("file")
    
    try:
        file_content = await file.read()
        max_size = 10 * 1024 * 1024  # 10MB
        
        if len(file_content) > max_size:
            raise FileTooLargeError(
                filename=file.filename,
                file_size=len(file_content),
                max_size=max_size
            )
    except Exception as e:
        raise FileProcessingError(
            filename=file.filename,
            operation="file reading",
            error=str(e)
        )
    
    # Check file type
    allowed_types = [
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/tiff",
        "image/bmp"
    ]
    
    if file.content_type not in allowed_types:
        raise UnsupportedFileTypeError(
            filename=file.filename,
            file_type=file.content_type,
            supported_types=allowed_types
        )
    
    try:
        filename = generate_filename()
        
        try:
            s3_key, s3_url = s3_service.upload_file(
                file_content=file_content,
                original_filename=file.filename,
                content_type=file.content_type
            )
        except Exception as e:
            raise S3ServiceError(
                operation="file upload",
                error=str(e)
            )

        db_document = Document(
            filename=filename,
            original_filename=file.filename,
            file_size=len(file_content),
            content_type=file.content_type,
            s3_key=s3_key,
            s3_url=s3_url,
            user_id=current_user.id
        )
        
        try:
            db.add(db_document)
            db.commit()
            db.refresh(db_document)
        except IntegrityError as e:
            db.rollback()
            raise DatabaseError(
                operation="document creation",
                table="documents",
                error=str(e)
            )
        except OperationalError as e:
            db.rollback()
            raise DatabaseConnectionError(str(e))
        
        try:
            await activity_logger.log_document_upload(
                db=db,
                user_id=current_user.id,
                document_id=db_document.id,
                details={
                    "filename": file.filename,
                    "file_size": len(file_content),
                    "content_type": file.content_type
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to log upload activity: {e}")

        if openai_service:
            background_tasks.add_task(
                process_document_with_ai,
                document_id=db_document.id,
                file_content=file_content,
                filename=file.filename,
                db=db
            )
        
        logger.info(f"✅ Document uploaded successfully: {file.filename} by user {current_user.username}")
        return DocumentSchema.from_orm(db_document)
        
    except (FileTooLargeError, UnsupportedFileTypeError, FileProcessingError, 
            S3ServiceError, DatabaseError, DatabaseConnectionError):
        raise
        
    except Exception as e:
        import traceback
        
        try:
            db.rollback()
        except:
            pass
        
        raise FileProcessingError(
            filename=file.filename,
            operation="document upload",
            error=str(e)
        )


async def process_document_with_ai(
    document_id: int,
    file_content: bytes,
    filename: str,
    db: Session
):
    """Background task to process document with AI"""
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found for AI processing")
            return
        
        if (document.extraction_status == "completed" and 
            document.extracted_data and
            document.patient_first_name and 
            document.patient_last_name and 
            document.patient_dob):
            logger.info(f"Document {document_id} already processed, skipping duplicate AI processing")
            return
        
        if document.extraction_status == "processing":
            logger.warning(f"Document {document_id} is already being processed by another task")
            return
        
        document.extraction_status = "processing"
        db.commit()
        
        logger.info(f"Starting AI processing for document {document_id}")
        
        extracted_data = await document_processor.process_document(file_content, filename)
        
        document.patient_first_name = extracted_data.get("patient_first_name")
        document.patient_last_name = extracted_data.get("patient_last_name")
        document.patient_dob = extracted_data.get("patient_dob")
        document.extracted_data = extracted_data
        document.extraction_status = "completed"
        document.extraction_error = None
        
        db.commit()
        
        await activity_logger.log_document_processing(
            db=db,
            user_id=document.user_id,
            document_id=document.id,
            details={
                "extraction_status": "completed",
                "extracted_data": extracted_data
            }
        )
        
        logger.info(f"Document {document_id} processed successfully with AI")
        
    except Exception as e:
        logger.error(f"AI processing error for document {document_id}: {e}")
        
        try:
            document.extraction_status = "failed"
            document.extraction_error = str(e)
            db.commit()
        except:
            db.rollback()


@router.get("/", response_model=PaginatedResponse)
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of documents"""
    try:
        query = db.query(Document).filter(Document.user_id == current_user.id)
        
        if status_filter:
            query = query.filter(Document.extraction_status == status_filter)
        
        total = query.count()
        
        documents = query.offset(skip).limit(limit).all()
        
        document_schemas = [DocumentSchema.from_orm(doc) for doc in documents]
        
        pages = (total + limit - 1) // limit
        page = (skip // limit) + 1
        
        return PaginatedResponse(
            items=document_schemas,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch documents"
        )


@router.get("/{document_id}", response_model=DocumentSchema)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific document by ID"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return DocumentSchema.from_orm(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch document"
        )


@router.post("/{document_id}/extract", response_model=DocumentExtractionResponse)
async def extract_document_data(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Manually trigger document data extraction"""
    try:
        if not openai_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service not available"
            )
        
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if (document.extracted_data and 
            document.extraction_status == "completed" and
            document.patient_first_name and 
            document.patient_last_name and 
            document.patient_dob):
            
            logger.info(f"Document {document_id} already processed with complete data, returning existing results")
            return DocumentExtractionResponse(
                success=True,
                extracted_data=document.extracted_data,
                cached=True,
                message="Document already processed with complete data"
            )
        
        if document.extraction_status == "processing":
            logger.warning(f"Document {document_id} is currently being processed")
            return DocumentExtractionResponse(
                success=False,
                error="Document is currently being processed. Please wait.",
                status="processing"
            )
        
        current_time = time.time()
        last_request_time = extraction_rate_limit.get(current_user.id, 0)
        if current_time - last_request_time < RATE_LIMIT_SECONDS:
            remaining_time = RATE_LIMIT_SECONDS - (current_time - last_request_time)
            logger.warning(f"Rate limit exceeded for user {current_user.id}, must wait {remaining_time:.1f}s")
            return DocumentExtractionResponse(
                success=False,
                error=f"Too many requests. Please wait {remaining_time:.1f} seconds before trying again.",
                status="rate_limited",
                retry_after=remaining_time
            )
        
        extraction_rate_limit[current_user.id] = current_time
        
        document.extraction_status = "processing"
        db.commit()
        
        try:
            file_content = s3_service.download_file(document.s3_key)
            
            if not file_content:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found in S3"
                )
            
            extracted_data = await document_processor.process_document(
                file_content, document.original_filename
            )
            
            document.patient_first_name = extracted_data.get("patient_first_name")
            document.patient_last_name = extracted_data.get("patient_last_name")
            document.patient_dob = extracted_data.get("patient_dob")
            document.extracted_data = extracted_data
            document.extraction_status = "completed"
            document.extraction_error = None
            
            db.commit()
            
            await activity_logger.log_document_processing(
                db=db,
                user_id=current_user.id,
                document_id=document.id,
                details={"manual_extraction": True, "extracted_data": extracted_data}
            )
            
            return DocumentExtractionResponse(
                success=True,
                extracted_data=extracted_data
            )
            
        except Exception as e:
            document.extraction_status = "failed"
            document.extraction_error = str(e)
            db.commit()
            
            return DocumentExtractionResponse(
                success=False,
                error=str(e)
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document extraction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract document data"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a document"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        s3_service.delete_file(document.s3_key)
        
        db.delete(document)
        db.commit()
        
        logger.info(f"Document deleted: {document.original_filename} by user {current_user.username}")
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )
