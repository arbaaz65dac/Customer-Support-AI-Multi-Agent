
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Order
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import create_order as create_order_service

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
):
    """HTTP endpoint for creating an order."""
    try:
        return create_order_service(db, order_data)
    except ValueError as exc:
        message = str(exc)

        if message == "Customer not found" or message.endswith("not found"):
            raise HTTPException(status_code=404, detail=message) from exc

        if message.startswith("Insufficient stock"):
            raise HTTPException(status_code=409, detail=message) from exc

        raise HTTPException(status_code=400, detail=message) from exc


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve an order for local development and testing."""
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    # TODO: Enforce ownership using the authenticated customer identity
    # before making this endpoint available in production.
    return order
