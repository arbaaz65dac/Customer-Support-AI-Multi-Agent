import json
import math
from decimal import Decimal
from typing import Literal

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Order, Product, SupportTicket
from app.schemas.support_ticket import SupportTicketCreate
from app.services.product_service import search_products as query_products
from app.services.refund_service import create_refund_request
from app.services.support_ticket_service import (
    create_support_ticket as create_ticket_record,
)


def _json_result(**payload) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _has_trusted_customer(customer_id: int | None) -> bool:
    return (
        isinstance(customer_id, int)
        and not isinstance(customer_id, bool)
        and customer_id > 0
    )


def create_support_tools(
    db: Session,
    trusted_customer_id: int | None = None,
):
    """Create bounded business tools using a verified customer identity."""

    @tool
    def search_products(
        query: str = "all",
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        limit: int = 10,
    ) -> str:
        """Search the active product catalogue with validated filters."""
        query = (query or "").strip()
        category = category.strip() if category else None
        if not query:
            return _json_result(error="Search query cannot be empty.")
        if query.lower() in {"all", "*"}:
            query = ""
        if len(query) > 100:
            return _json_result(
                error="Search query must be 100 characters or fewer."
            )
        if category and len(category) > 100:
            return _json_result(
                error="Category must be 100 characters or fewer."
            )
        if not 1 <= limit <= 20:
            return _json_result(error="Limit must be between 1 and 20.")
        if max_price is not None and (
            not math.isfinite(max_price)
            or max_price <= 0
            or max_price > 1_000_000
        ):
            return _json_result(
                error="Maximum price must be between 0 and 1000000."
            )
        if min_price is not None and (
            not math.isfinite(min_price)
            or min_price <= 0
            or min_price > 1_000_000
        ):
            return _json_result(
                error="Minimum price must be between 0 and 1000000."
            )
        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):
            return _json_result(
                error="Minimum price cannot exceed maximum price."
            )

        products = query_products(
            db=db,
            query=query or None,
            category=category,
            min_price=(
                Decimal(str(min_price)) if min_price is not None else None
            ),
            max_price=(
                Decimal(str(max_price)) if max_price is not None else None
            ),
            limit=limit,
        )
        return _json_result(
            count=len(products),
            products=[
                {
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "category": product.category,
                    "price": str(product.price),
                    "stock": product.stock,
                }
                for product in products
            ],
        )

    @tool
    def get_product_details(product_id: int) -> str:
        """Return details for one active product by its catalogue ID."""
        if product_id <= 0:
            return _json_result(
                found=False, error="Product ID must be positive."
            )
        product = db.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.active.is_(True),
            )
        )
        if product is None:
            return _json_result(found=False, message="Product not found.")
        return _json_result(
            found=True,
            product={
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "category": product.category,
                "price": str(product.price),
                "stock": product.stock,
            },
        )

    @tool
    def get_order_status(order_id: int) -> str:
        """Look up one order belonging to the authenticated customer."""
        if order_id <= 0:
            return _json_result(
                found=False, error="Order ID must be a positive integer."
            )
        if not _has_trusted_customer(trusted_customer_id):
            return _json_result(
                found=False,
                error="Order lookup requires an authenticated customer.",
            )
        order = db.scalar(
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.id == order_id,
                Order.customer_id == trusted_customer_id,
            )
        )
        if order is None:
            return _json_result(found=False, message="Order not found.")
        return _json_result(
            found=True,
            order={
                "id": order.id,
                "status": order.status,
                "created_at": (
                    order.created_at.isoformat() if order.created_at else None
                ),
                "items": [
                    {
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                    }
                    for item in order.items
                ],
            },
        )

    @tool
    def list_my_orders(limit: int = 10) -> str:
        """List recent orders for the authenticated customer only."""
        if not 1 <= limit <= 20:
            return _json_result(error="Limit must be between 1 and 20.")
        if not _has_trusted_customer(trusted_customer_id):
            return _json_result(
                error="Order listing requires an authenticated customer."
            )
        orders = db.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.customer_id == trusted_customer_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .limit(limit)
        ).all()
        return _json_result(
            count=len(orders),
            orders=[
                {
                    "id": order.id,
                    "status": order.status,
                    "created_at": (
                        order.created_at.isoformat()
                        if order.created_at
                        else None
                    ),
                    "items": [
                        {
                            "product_id": item.product_id,
                            "quantity": item.quantity,
                            "unit_price": str(item.unit_price),
                        }
                        for item in order.items
                    ],
                }
                for order in orders
            ],
        )

    @tool
    def create_support_ticket(subject: str, description: str) -> str:
        """Create a support ticket for the authenticated customer."""
        if not _has_trusted_customer(trusted_customer_id):
            return _json_result(
                success=False,
                error="Ticket creation requires an authenticated customer.",
            )
        subject = (subject or "").strip()
        description = (description or "").strip()
        if not 3 <= len(subject) <= 200:
            return _json_result(
                success=False,
                error="Subject must contain between 3 and 200 characters.",
            )
        if not 5 <= len(description) <= 5000:
            return _json_result(
                success=False,
                error="Description must contain between 5 and 5000 characters.",
            )
        ticket = create_ticket_record(
            db=db,
            ticket_data=SupportTicketCreate(
                subject=subject, description=description
            ),
            customer_id=trusted_customer_id,
        )
        return _json_result(
            success=True,
            ticket_id=ticket.id,
            subject=ticket.subject,
            status=ticket.status,
        )

    @tool
    def get_ticket_status(ticket_id: int) -> str:
        """Get a support ticket status only for its authenticated owner."""
        if ticket_id <= 0:
            return _json_result(
                found=False, error="Ticket ID must be positive."
            )
        if not _has_trusted_customer(trusted_customer_id):
            return _json_result(
                found=False,
                error="Ticket lookup requires an authenticated customer.",
            )
        ticket = db.scalar(
            select(SupportTicket).where(
                SupportTicket.id == ticket_id,
                SupportTicket.customer_id == trusted_customer_id,
            )
        )
        if ticket is None:
            return _json_result(found=False, message="Support ticket not found.")
        return _json_result(
            found=True,
            ticket={
                "id": ticket.id,
                "subject": ticket.subject,
                "status": ticket.status,
                "priority": ticket.priority,
                "created_at": (
                    ticket.created_at.isoformat()
                    if ticket.created_at
                    else None
                ),
            },
        )

    @tool
    def request_refund(
        order_id: int,
        reason: str,
        request_type: Literal["return", "refund"] = "refund",
    ) -> str:
        """Create a tracked return/refund request; never executes a payment."""
        if not _has_trusted_customer(trusted_customer_id):
            return _json_result(
                success=False,
                error="A refund request requires an authenticated customer.",
            )
        if order_id <= 0:
            return _json_result(success=False, error="Order ID must be positive.")
        reason = (reason or "").strip()
        if not 5 <= len(reason) <= 5000:
            return _json_result(
                success=False,
                error="Reason must contain between 5 and 5000 characters.",
            )
        if request_type not in {"return", "refund"}:
            return _json_result(
                success=False, error="Request type must be return or refund."
            )
        try:
            request = create_refund_request(
                db=db,
                customer_id=trusted_customer_id,
                order_id=order_id,
                request_type=request_type,
                reason=reason,
            )
        except ValueError as exc:
            return _json_result(success=False, error=str(exc))
        return _json_result(
            success=True,
            request_id=request.id,
            order_id=request.order_id,
            request_type=request.request_type,
            status=request.status,
            message="Your request was recorded for administrator review.",
        )

    return [
        search_products,
        get_product_details,
        get_order_status,
        list_my_orders,
        create_support_ticket,
        get_ticket_status,
        request_refund,
    ]
