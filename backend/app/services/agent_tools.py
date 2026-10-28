import json
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Order
from app.services.product_service import search_products


def create_support_tools(db: Session):
    """
    Build tools that use the current database session.

    The LLM receives the tool descriptions and schemas.
    The Python functions below control the actual database access.
    """

    @tool
    def search_product_catalog(
        query: str,
        max_price: float | None = None,
    ) -> str:
        """
        Search active products by name or description.
        Optionally restrict results to a maximum price.
        """
        # Reject empty or excessively long searches.
        query = query.strip()
        if not query:
            return json.dumps({
                "error": "Search query cannot be empty."
            })

        if len(query) > 100:
            return json.dumps({
                "error": "Search query must be 100 characters or fewer."
            })

        # Reject nonsensical price limits before querying the database.
        if max_price is not None and (
            max_price <= 0 or max_price > 1_000_000
        ):
            return json.dumps({
                "error": "Maximum price must be between 0 and 1000000."
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
    def lookup_order_status(
        order_id: int,
        customer_id: int,
    ) -> str:
        """
        Look up an order's status for a supplied customer ID.

        Use when a user asks about an existing order.
        Both identifiers are required for this development tool.
        Never invent order details if no matching order exists.
        """
        if order_id <= 0 or customer_id <= 0:
            return json.dumps({
                "error": "Order ID and customer ID must be positive integers."
            })
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

        return json.dumps({
            "found": True,
            "order_id": order.id,
            "status": order.status,
            "created_at": order.created_at.isoformat()
            if order.created_at
            else None,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": str(item.unit_price),
                }
                for item in order.items
            ],
        })

    # Only these explicitly defined functions are exposed to the model.
    return [search_product_catalog, lookup_order_status]