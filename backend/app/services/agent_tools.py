
import json
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Order
from app.services.product_service import search_products


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

        # Validate the requested order ID.
        if order_id <= 0:
            return json.dumps({
                "found": False,
                "error": "Order ID must be one of the required positive integers.",
            })

        # Do not perform a customer-specific lookup without a
        # trusted customer identity from the application.
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

        # Match BOTH IDs. The model cannot choose the customer ID.
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.id == order_id,
                Order.customer_id == trusted_customer_id,
            )
        )

        order = db.scalar(statement)

        # Use a generic response to avoid revealing whether an order
        # belongs to a different customer.
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

    # Expose only these explicitly approved tools to the LLM.
    return [
        search_product_catalog,
        lookup_order_status,
    ]
