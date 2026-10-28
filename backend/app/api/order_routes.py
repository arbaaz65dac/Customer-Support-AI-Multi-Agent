
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Customer, Order, OrderItem, Product
from app.schemas.order import OrderCreate, OrderResponse

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
    """Create an order and reserve stock in one transaction."""

    try:
        # Verify the customer exists.
        customer = db.get(Customer, order_data.customer_id)
        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer not found",
            )

        # Combine repeated product IDs to simplify stock checks.
        requested = {}
        for item in order_data.items:
            requested[item.product_id] = (
                requested.get(item.product_id, 0) + item.quantity
            )

        # Lock product rows while checking and updating inventory.
        # This helps prevent concurrent orders overselling the same stock.
        product_ids = sorted(requested.keys())
        products = db.scalars(
            select(Product)
            .where(Product.id.in_(product_ids))
            .order_by(Product.id)
            .with_for_update()
        ).all()

        product_by_id = {product.id: product for product in products}

        # Validate every product before changing inventory.
        for product_id, quantity in requested.items():
            product = product_by_id.get(product_id)

            if product is None or not product.active:
                raise HTTPException(
                    status_code=404,
                    detail=f"Active product {product_id} not found",
                )

            if product.stock < quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Insufficient stock for product {product_id}",
                )

        # Create the order only after all checks have passed.
        order = Order(
            customer_id=order_data.customer_id,
            status="pending",
        )
        db.add(order)
        db.flush()  # Assign an order ID without committing yet.

        # Record the purchase price and decrement inventory.
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

        db.commit()

        # Reload relationships so the response contains the order items.
        saved_order = db.scalar(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order.id)
        )
        return saved_order

    except Exception:
        # Roll back all pending changes if anything goes wrong.
        db.rollback()
        raise


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
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    # TODO: Before production, enforce that the authenticated customer
    # owns this order. An order ID alone is not authorization.
    return order
