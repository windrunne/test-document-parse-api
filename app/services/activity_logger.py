from sqlalchemy.orm import Session
from app.models import UserActivity
from app.schemas import UserActivityCreate
from app.database import get_db
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ActivityLogger:
    
    @staticmethod
    async def log_activity(
        db: Session,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserActivity:
        try:
            activity_data = UserActivityCreate(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details
            )
            
            db_activity = UserActivity(
                **activity_data.dict(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.add(db_activity)
            db.commit()
            db.refresh(db_activity)
            
            logger.info(f"Activity logged: {action} on {resource_type} by user {user_id}")
            return db_activity
            
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            db.rollback()
            raise
    
    @staticmethod
    async def log_login(db: Session, user_id: int, ip_address: str, user_agent: str):
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            action="login",
            resource_type="auth",
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    async def log_logout(db: Session, user_id: int, ip_address: str, user_agent: str):
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            action="logout",
            resource_type="auth",
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    async def log_order_creation(db: Session, user_id: int, order_id: int, details: Optional[Dict] = None):
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            action="create",
            resource_type="order",
            resource_id=order_id,
            details=details
        )
    
    @staticmethod
    async def log_order_update(db: Session, user_id: int, order_id: int, details: Optional[Dict] = None):
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            action="update",
            resource_type="order",
            resource_id=order_id,
            details=details
        )
    
    @staticmethod
    async def log_order_deletion(db: Session, user_id: int, order_id: int, details: Optional[Dict] = None):
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            action="delete",
            resource_type="order",
            resource_id=order_id,
            details=details
        )
    
    @staticmethod
    async def log_document_upload(db: Session, user_id: int, document_id: int, details: Optional[Dict] = None):
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            action="upload",
            resource_type="document",
            resource_id=document_id,
            details=details
        )
    
    @staticmethod
    async def log_document_processing(db: Session, user_id: int, document_id: int, details: Optional[Dict] = None):
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            action="process",
            resource_type="document",
            resource_id=document_id,
            details=details
        )
    
    @staticmethod
    async def log_api_access(db: Session, user_id: int, endpoint: str, method: str, details: Optional[Dict] = None):
        return await ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            action=f"{method}_{endpoint}",
            resource_type="api",
            details=details
        )


activity_logger = ActivityLogger()
