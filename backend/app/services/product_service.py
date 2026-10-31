
from decimal import Decimal
import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Product


def search_products(
    db: Session,
    query: str | None = None,
    category: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Product]:
    """
    Search active products using controlled filters.

    This function contains business/data-access logic, not HTTP logic.
    It can be reused by an API route or a future LangChain tool.
    """
    statement = select(Product).where(Product.active.is_(True))

    if query and query.strip():
        # Match every useful query word, even when words are not adjacent in
        # the product description (for example, "wireless headphones").
        terms = re.findall(r"[\w]+", query.strip(), flags=re.UNICODE)
        for word in terms:
            term = f"%{word}%"
            statement = statement.where(
                or_(
                    Product.name.ilike(term),
                    Product.description.ilike(term),
                )
            )

    if category and category.strip():
        statement = statement.where(
            Product.category == category.strip()
        )

    if max_price is not None:
        statement = statement.where(Product.price <= max_price)

    if min_price is not None:
        statement = statement.where(Product.price >= min_price)

    statement = (
        statement
        .order_by(Product.id)
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())
