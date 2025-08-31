from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from typing import List, Optional
from app.database import get_db
from app.models import Order, User
from app.schemas import OrderCreate, OrderUpdate, Order as OrderSchema, PaginatedResponse
from app.api.deps import get_current_active_user, log_api_activity
from app.services.activity_logger import activity_logger
from app.core.exceptions import (
    ResourceNotFoundError,
    ResourceAccessDeniedError,
    ValidationError,
    RequiredFieldError,
    DatabaseError,
    DatabaseConnectionError
)
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


def generate_order_number() -> str:
    """Generate unique order number"""
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


@router.post("/", response_model=OrderSchema)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Create a new order"""
    try:
        order_number = generate_order_number()
        
        total_amount = order_data.quantity * order_data.unit_price
        
        order_dict = order_data.dict()
        if 'total_amount' in order_dict:
            del order_dict['total_amount']
        
        db_order = Order(
            **order_dict,
            order_number=order_number,
            total_amount=total_amount,
            user_id=current_user.id
        )
        
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        
        try:
            await activity_logger.log_order_creation(
                db=db,
                user_id=current_user.id,
                order_id=db_order.id,
                details={
                    "order_number": order_number,
                    "patient_name": f"{order_data.patient_first_name} {order_data.patient_last_name}"
                }
            )
        except Exception as activity_error:
            logger.error(f"Activity logging failed: {activity_error}")
        
        return OrderSchema.from_orm(db_order)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )


@router.get("/", response_model=PaginatedResponse)
async def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None),
    patient_name: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of orders"""
    try:
        query = db.query(Order).filter(Order.user_id == current_user.id)
        if status_filter:
            query = query.filter(Order.status == status_filter)
        
        if patient_name:
            query = query.filter(
                (Order.patient_first_name.ilike(f"%{patient_name}%")) |
                (Order.patient_last_name.ilike(f"%{patient_name}%"))
            )
        
        total = query.count()
        
        orders = query.offset(skip).limit(limit).all()
        
        order_schemas = [OrderSchema.from_orm(order) for order in orders]
        
        pages = (total + limit - 1) // limit
        page = (skip // limit) + 1
        
        return PaginatedResponse(
            items=order_schemas,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch orders"
        )


@router.get("/{order_id}", response_model=OrderSchema)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific order by ID"""
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        return OrderSchema.from_orm(order)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch order"
        )


@router.put("/{order_id}", response_model=OrderSchema)
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an existing order"""
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        update_data = order_data.dict(exclude_unset=True)
        
        if 'quantity' in update_data or 'unit_price' in update_data:
            new_quantity = update_data.get('quantity', order.quantity)
            new_unit_price = update_data.get('unit_price', order.unit_price)
            update_data['total_amount'] = new_quantity * new_unit_price
        
        for field, value in update_data.items():
            setattr(order, field, value)
        
        db.commit()
        db.refresh(order)
        
        await activity_logger.log_order_update(
            db=db,
            user_id=current_user.id,
            order_id=order.id,
            details={"updated_fields": list(update_data.keys())}
        )
        
        return OrderSchema.from_orm(order)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order"
        )


@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an order"""
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order_number = order.order_number
        
        db.delete(order)
        db.commit()
        
        await activity_logger.log_order_deletion(
            db=db,
            user_id=current_user.id,
            order_id=order_id,
            details={"order_number": order_number}
        )
        
        return {"message": "Order deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete order"
        )


@router.get("/{order_id}/status")
async def get_order_status(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get order status"""
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        ).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "created_at": order.created_at,
            "updated_at": order.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch order status"
        )
