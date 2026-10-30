
import json
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Order
from app.schemas.support_ticket import SupportTicketCreate
from app.services.product_service import search_products
from app.services.support_ticket_service import create_support_ticket


def create_support_tools(
    db: Session,
    trusted_customer_id: int | None = None,
):
    """
    Create support tools using the current database session.

    trusted_customer_id must come from trusted application context,
    such as a verified authentication dependency. Never obtain it
    from the LLM or from free-form customer messages.
    """

    @tool
    def search_product_catalog(
        query: str = "all",
        max_price: float | None = None,
    ) -> str:
        """
        Search active products by name or description.

        Use query="all" for price-only searches or the full catalog.
        Supply max_price to filter products by their maximum price.
        """

        query = (query or "").strip()

        if not query:
            return json.dumps({
                "error": "Search query cannot be empty."
            })

        if query.lower() in {"all", "*"}:
            query = None

        if query is not None and len(query) > 100:
            return json.dumps({
                "error": "Search query must be 100 characters or fewer."
            })

        if max_price is not None and (
            max_price <= 0 or max_price > 1_000_000
        ):
            return json.dumps({
                "error": (
                    "Maximum price must be between 0 and 1000000."
                )
            })

        products = search_products(
            db=db,
            query=query,
            max_price=(
                Decimal(str(max_price))
                if max_price is not None
                else None
            ),
            limit=10,
            offset=0,
        )

        results = [
            {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "category": product.category,
                "price": str(product.price),
                "stock": product.stock,
            }
            for product in products
        ]

        return json.dumps({
            "count": len(results),
            "products": results,
        })

    @tool
    def lookup_order_status(order_id: int) -> str:
        """
        Look up an order belonging to the authenticated customer.

        Only the order ID comes from the tool call. The customer ID
        must come from trusted application context.
        """

        if order_id <= 0:
            return json.dumps({
                "found": False,
                "error": (
                    "Order ID must be one of the required positive integers."
                ),
            })

        if (
            trusted_customer_id is None
            or trusted_customer_id <= 0
        ):
            return json.dumps({
                "found": False,
                "error": (
                    "Order lookup requires an authenticated customer."
                ),
            })

        # Restrict the query to the authenticated customer's orders.
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.id == order_id,
                Order.customer_id == trusted_customer_id,
            )
        )

        order = db.scalar(statement)

        # Do not reveal whether an order belongs to another customer.
        if order is None:
            return json.dumps({
                "found": False,
                "message": (
                    "No order was found matching the supplied "
                    "order ID and authenticated customer."
                ),
            })

        return json.dumps({
            "found": True,
            "order_id": order.id,
            "customer_id": order.customer_id,
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
        })

    @tool
    def create_customer_support_ticket(
        subject: str,
        description: str,
    ) -> str:
        """
        Create a support ticket for the authenticated customer.

        Use this tool when a customer explicitly requests a support
        ticket or needs an issue recorded for follow-up.

        The customer ID must never be supplied by the model.
        It is taken exclusively from trusted application context.
        """

        if (
            trusted_customer_id is None
            or trusted_customer_id <= 0
        ):
            return json.dumps({
                "success": False,
                "error": (
                    "Ticket creation requires an authenticated customer."
                ),
            })

        subject = (subject or "").strip()
        description = (description or "").strip()

        if not 3 <= len(subject) <= 200:
            return json.dumps({
                "success": False,
                "error": (
                    "Subject must contain between 3 and 200 characters."
                ),
            })

        if not 5 <= len(description) <= 5000:
            return json.dumps({
                "success": False,
                "error": (
                    "Description must contain between 5 and 5000 characters."
                ),
            })

        ticket_data = SupportTicketCreate(
            subject=subject,
            description=description,
        )

        # Reuse the existing service for persistence and transaction handling.
        ticket = create_support_ticket(
            db=db,
            ticket_data=ticket_data,
            customer_id=trusted_customer_id,
        )

        return json.dumps({
            "success": True,
            "ticket_id": ticket.id,
            "subject": ticket.subject,
            "status": ticket.status,
            "message": (
                f"Support ticket #{ticket.id} was created successfully."
            ),
        })

    # Expose only explicitly approved tools to the LLM.
    return [
        search_product_catalog,
        lookup_order_status,
        create_customer_support_ticket,
    ]
