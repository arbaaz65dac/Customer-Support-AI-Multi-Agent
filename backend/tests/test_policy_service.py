from datetime import datetime, timedelta, timezone

import pytest

from app.models import Customer, Order
from app.services.policy_service import get_return_window_days
from app.services.refund_service import create_refund_request


def test_return_window_is_read_from_versioned_policy():
    assert get_return_window_days() == 7


def test_return_window_uses_latest_policy_version(tmp_path, monkeypatch):
    from app.services import policy_service

    monkeypatch.setattr(policy_service, "KNOWLEDGE_BASE_DIR", tmp_path)
    (tmp_path / "returns_policy_v1.md").write_text(
        "Return window days: 7\n", encoding="utf-8"
    )
    (tmp_path / "returns_policy_v2.md").write_text(
        "Return window days: 10\n", encoding="utf-8"
    )

    assert policy_service.get_return_window_days() == 10


def test_refund_service_rejects_request_outside_policy_window(db_session):
    customer = Customer(
        name="Expired Request Customer",
        email="expired-window@example.com",
        password_hash="test-hash",
    )
    db_session.add(customer)
    db_session.flush()
    order = Order(
        customer_id=customer.id,
        status="delivered",
        delivered_at=(
            datetime.now(timezone.utc).replace(tzinfo=None)
            - timedelta(days=8)
        ),
    )
    db_session.add(order)
    db_session.commit()

    with pytest.raises(ValueError, match="window has expired"):
        create_refund_request(
            db=db_session,
            customer_id=customer.id,
            order_id=order.id,
            request_type="return",
            reason="The item does not meet expectations.",
        )


def test_refund_service_allows_last_calendar_day_of_policy_window(db_session):
    customer = Customer(
        name="Last Day Customer",
        email="last-window-day@example.com",
        password_hash="test-hash",
    )
    db_session.add(customer)
    db_session.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    delivery_date = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ) - timedelta(days=7)
    order = Order(
        customer_id=customer.id,
        status="delivered",
        delivered_at=delivery_date,
    )
    db_session.add(order)
    db_session.commit()

    request = create_refund_request(
        db=db_session,
        customer_id=customer.id,
        order_id=order.id,
        request_type="return",
        reason="The item does not meet expectations.",
    )

    assert request.status == "pending"


def test_refund_service_requires_verified_delivery_date(db_session):
    customer = Customer(
        name="Missing Delivery Date",
        email="missing-delivered-at@example.com",
        password_hash="test-hash",
    )
    db_session.add(customer)
    db_session.flush()
    order = Order(customer_id=customer.id, status="delivered")
    db_session.add(order)
    db_session.commit()

    with pytest.raises(ValueError, match="delivery date is unavailable"):
        create_refund_request(
            db=db_session,
            customer_id=customer.id,
            order_id=order.id,
            request_type="refund",
            reason="The item arrived damaged.",
        )
