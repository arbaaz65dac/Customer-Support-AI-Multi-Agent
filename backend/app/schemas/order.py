
from datetime import datetime
from decimal import Decimal

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    # Product selected by the customer.
    product_id: int = Field(gt=0)

    # Quantity must be at least one.
    quantity: int = Field(ge=1, le=100)


class OrderCreate(BaseModel):
    # Development only: production must derive customer_id
    # from the authenticated user's identity.
    customer_id: int = Field(gt=0)

    # An order must contain at least one item.
    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str | None = None
    quantity: int
    unit_price: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    status: str
    created_at: datetime
    delivered_at: datetime | None = None
    items: list[OrderItemResponse]


class OrderStatusUpdate(BaseModel):
    status: Literal[
        "pending", "processing", "shipped", "delivered", "cancelled"
    ]
