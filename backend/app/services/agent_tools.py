
import json
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Order
from app.services.product_service import search_products


def create_support_tools(db: Session):
    """
    Build support tools using the current database session.

    The LLM receives the tool descriptions and schemas.
    The Python functions control database access and validate inputs.
    """

    @tool
    def search_product_catalog(
        query: str = "all",
        max_price: float | None = None,
    ) -> str:
        """
        Search active products by name, description, or category.

        Examples:
        - Find products under 2000:
          query="all", max_price=2000
        - Find a wireless mouse:
          query="wireless mouse"
        - Find laptops under 50000:
          query="laptop", max_price=50000
        - Show all products:
          query="all"

        For price-only searches, use query="all" and set max_price.
        Empty queries are invalid.
        """

        # Normalize the query without silently accepting blank input.
        query = (query or "").strip()

        # Reject empty or whitespace-only queries.
        if not query:
            return json.dumps({
                "error": "Search query cannot be empty."
            })

        # Treat "all" and "*" as requests to search the full catalog.
        # Passing None prevents searching for the literal word "all".
        if query.lower() in {"all", "*"}:
            query = None

        # Validate specific search terms.
        if query is not None and len(query) > 100:
            return json.dumps({
                "error": "Search query must be 100 characters or fewer."
            })

        # Validate the optional maximum price.
        if max_price is not None and (
            max_price <= 0 or max_price > 1_000_000
        ):
            return json.dumps({
                "error": (
                    "Maximum price must be between 0 and 1000000."
                )
            })

        # Search active products. When query is None, the name and
        # description filters are skipped, allowing price-only searches.
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
    def lookup_order_status(
        order_id: int,
        customer_id: int,
    ) -> str:
        """
        Look up an order's status using its order ID and customer ID.

        Both identifiers are required. Never invent order details
        or identifiers when looking up an order.
        """

        # Reject invalid identifiers.
        if order_id <= 0 or customer_id <= 0:
            return json.dumps({
                "error": (
                    "Order ID and customer ID must be positive integers."
                )
            })

        # Load the matching order and its associated items.
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.id == order_id,
                Order.customer_id == customer_id,
            )
        )

        order = db.scalar(statement)

        if order is None:
            return json.dumps({
                "found": False,
                "message": "No matching order was found.",
            })

        # Return the relevant order information.
        return json.dumps({
            "found": True,
            "order_id": order.id,
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

    # Expose only the explicitly defined support tools.
    return [
        search_product_catalog,
        lookup_order_status,
    ]
