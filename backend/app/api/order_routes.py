
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import get_current_customer, require_admin
from app.database import get_db
from app.models import Customer, Order, OrderItem
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.order_service import create_order as create_order_service


router = APIRouter(
    prefix="/api/orders",
    tags=["Orders"],
)


@router.get("/admin/all", response_model=list[OrderResponse])
def get_all_orders(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    return db.scalars(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = status_data.status
    if status_data.status == "delivered" and order.delivered_at is None:
        order.delivered_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return db.scalar(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id)
    )


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """Create an order for the authenticated customer."""

    # Never trust the customer ID supplied in the request body.
    # Use the identity established by JWT authentication instead.
    order_data.customer_id = current_customer.id

    try:
        return create_order_service(db, order_data)

    except ValueError as exc:
        message = str(exc)

        if message == "Customer not found" or message.endswith("not found"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        if message.startswith("Insufficient stock"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc


@router.get(
    "",
    response_model=list[OrderResponse],
)
def get_customer_orders(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """List orders belonging only to the authenticated customer."""

    orders = db.scalars(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.customer_id == current_customer.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).all()

    return orders


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """Retrieve an order only if it belongs to the authenticated customer."""

    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(
            Order.id == order_id,
            Order.customer_id == current_customer.id,
        )
    )

    if order is None:
        # Use the same response for missing orders and orders owned
        # by another customer to avoid disclosing their existence.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return order
