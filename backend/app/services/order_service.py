
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Customer, Order, OrderItem, Product
from app.schemas.order import OrderCreate


def create_order(db: Session, order_data: OrderCreate) -> Order:
    """
    Create an order and reduce inventory in one transaction.

    This service contains business logic and can later be called
    by both FastAPI routes and controlled LangChain tools.
    """
    try:
        # Confirm the customer exists.
        customer = db.get(Customer, order_data.customer_id)
        if customer is None:
            raise ValueError("Customer not found")

        # Combine duplicate product IDs to calculate required stock.
        requested: dict[int, int] = {}
        for item in order_data.items:
            requested[item.product_id] = (
                requested.get(item.product_id, 0) + item.quantity
            )

        # Lock product rows in a consistent order during the transaction.
        product_ids = sorted(requested.keys())
        products = db.scalars(
            select(Product)
            .where(Product.id.in_(product_ids))
            .order_by(Product.id)
            .with_for_update()
        ).all()

        product_by_id = {product.id: product for product in products}

        # Validate every requested product before making changes.
        for product_id, quantity in requested.items():
            product = product_by_id.get(product_id)

            if product is None or not product.active:
                raise ValueError(f"Active product {product_id} not found")

            if product.stock < quantity:
                raise ValueError(
                    f"Insufficient stock for product {product_id}"
                )

        # Create the order inside the same transaction.
        order = Order(
            customer_id=order_data.customer_id,
            status="pending",
        )
        db.add(order)
        db.flush()

        # Record purchase-time prices and reserve inventory.
        for product_id, quantity in requested.items():
            product = product_by_id[product_id]
            product.stock -= quantity

            order.items.append(
                OrderItem(
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=product.price,
                )
            )

        order_id = order.id
        db.commit()

        # Load order items before returning the saved order.
        saved_order = db.scalar(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )

        if saved_order is None:
            raise RuntimeError("Created order could not be reloaded")

        return saved_order

    except Exception:
        # Roll back any uncommitted changes before propagating the error.
        db.rollback()
        raise
