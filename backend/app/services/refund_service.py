from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order, RefundRequest
from app.services.policy_service import get_return_window_days


def create_refund_request(
    db: Session,
    customer_id: int,
    order_id: int,
    request_type: str,
    reason: str,
) -> RefundRequest:
    """Persist an eligible, owner-verified refund/return request."""
    if customer_id <= 0:
        raise ValueError("A valid customer is required.")
    if request_type not in {"return", "refund"}:
        raise ValueError("Request type must be return or refund.")
    reason = reason.strip()
    if not 5 <= len(reason) <= 5000:
        raise ValueError(
            "Reason must contain between 5 and 5000 characters."
        )

    try:
        order = db.scalar(
            select(Order).where(
                Order.id == order_id,
                Order.customer_id == customer_id,
            )
        )
        if order is None:
            raise ValueError("Order not found.")
        if order.status != "delivered":
            raise ValueError(
                "Return or refund requests require a delivered order."
            )
        if order.delivered_at is None:
            raise ValueError(
                "The delivery date is unavailable; support must review this request."
            )
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        if order.delivered_at > current_time:
            raise ValueError(
                "The recorded delivery date is invalid; support must review this request."
            )
        return_window = get_return_window_days()
        last_eligible_date = order.delivered_at.date() + timedelta(
            days=return_window
        )
        if current_time.date() > last_eligible_date:
            raise ValueError(
                f"The {return_window}-day return request window has expired."
            )

        pending = db.scalar(
            select(RefundRequest).where(
                RefundRequest.order_id == order.id,
                RefundRequest.customer_id == customer_id,
                RefundRequest.status == "pending",
            )
        )
        if pending is not None:
            raise ValueError(
                "A request for this order is already pending review."
            )

        request = RefundRequest(
            customer_id=customer_id,
            order_id=order.id,
            request_type=request_type,
            reason=reason,
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request
    except Exception:
        db.rollback()
        raise
