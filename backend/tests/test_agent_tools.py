
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.services.agent_tools import create_support_tools
from app.models import (
    Customer,
    Order,
    OrderItem,
    Product,
    RefundRequest,
    SupportTicket,
)


def get_tool(db_session, name, trusted_customer_id=None):
    return next(
        support_tool
        for support_tool in create_support_tools(
            db_session, trusted_customer_id=trusted_customer_id
        )
        if support_tool.name == name
    )


def get_order_tool(db_session, trusted_customer_id=None):
    """Get the order lookup tool with an optional trusted customer ID."""
    tools = create_support_tools(
        db_session,
        trusted_customer_id=trusted_customer_id,
    )

    return next(
        tool
        for tool in tools
        if tool.name == "get_order_status"
    )


def get_product_tool(db_session):
    """Get the product search tool."""
    tools = create_support_tools(db_session)

    return next(
        tool
        for tool in tools
        if tool.name == "search_products"
    )

def get_ticket_tool(db_session, trusted_customer_id=None):
    """Get the support ticket tool with an optional trusted customer ID."""
    tools = create_support_tools(
        db_session,
        trusted_customer_id=trusted_customer_id,
    )

    return next(
        tool
        for tool in tools
        if tool.name == "create_support_ticket"
    )


def test_product_tool_rejects_empty_query(db_session):
    product_tool = get_product_tool(db_session)

    result = json.loads(
        product_tool.invoke({"query": "   "})
    )

    assert "error" in result
    assert "empty" in result["error"].lower()


def test_product_search_applies_price_and_category_filters(db_session):
    db_session.add_all(
        [
            Product(
                name="Wireless Headphones",
                description="Wireless audio",
                category="Audio",
                price="2500.00",
                stock=4,
                active=True,
            ),
            Product(
                name="Wired Headphones",
                description="Wired audio",
                category="Audio",
                price="1200.00",
                stock=3,
                active=True,
            ),
            Product(
                name="Wireless Mouse",
                description="Wireless accessory",
                category="Accessories",
                price="800.00",
                stock=5,
                active=True,
            ),
        ]
    )
    db_session.commit()

    result = json.loads(
        get_product_tool(db_session).invoke(
            {
                "query": "wireless",
                "category": "Audio",
                "min_price": 2000,
                "max_price": 3000,
            }
        )
    )

    assert result["count"] == 1
    assert result["products"][0]["name"] == "Wireless Headphones"


def test_product_search_rejects_invalid_price_range(db_session):
    result = json.loads(
        get_product_tool(db_session).invoke(
            {"query": "all", "min_price": 500, "max_price": 100}
        )
    )

    assert "cannot exceed" in result["error"]


def test_product_tool_rejects_excessive_query_length(db_session):
    product_tool = get_product_tool(db_session)

    result = json.loads(
        product_tool.invoke({"query": "a" * 101})
    )

    assert "error" in result
    assert "100 characters" in result["error"]


@pytest.mark.parametrize("max_price", [0, -1, 1_000_001])
def test_product_tool_rejects_invalid_max_price(db_session, max_price):
    product_tool = get_product_tool(db_session)

    result = json.loads(
        product_tool.invoke({
            "query": "all",
            "max_price": max_price,
        })
    )

    assert "error" in result
    assert "Maximum price" in result["error"]


def test_order_tool_rejects_non_positive_ids(db_session):
    order_tool = get_order_tool(
        db_session,
        trusted_customer_id=1,
    )

    result = json.loads(
        order_tool.invoke({"order_id": 0})
    )

    assert result["found"] is False
    assert "error" in result
    assert "positive integer" in result["error"]


def test_order_tool_requires_trusted_customer_id(db_session):
    order_tool = get_order_tool(db_session)

    result = json.loads(
        order_tool.invoke({"order_id": 999999})
    )

    assert result["found"] is False
    assert "error" in result
    assert "authenticated customer" in result["error"].lower()


def test_order_tool_returns_not_found_for_missing_order(db_session):
    order_tool = get_order_tool(
        db_session,
        trusted_customer_id=999999,
    )

    result = json.loads(
        order_tool.invoke({"order_id": 999999})
    )

    assert result["found"] is False
    assert "message" in result


def test_order_tool_rejects_non_positive_trusted_customer_id(db_session):
    order_tool = get_order_tool(
        db_session,
        trusted_customer_id=0,
    )

    result = json.loads(
        order_tool.invoke({"order_id": 1})
    )

    assert result["found"] is False
    assert "error" in result
    assert "authenticated customer" in result["error"].lower()


def test_order_tool_schema_does_not_expose_customer_id(db_session):
    order_tool = get_order_tool(
        db_session,
        trusted_customer_id=1,
    )

    schema = order_tool.args_schema.model_json_schema()

    assert "order_id" in schema["properties"]
    assert "customer_id" not in schema["properties"]


def test_required_tool_surface_has_no_customer_id_arguments(db_session):
    tools = create_support_tools(db_session, trusted_customer_id=1)
    expected_names = {
        "search_products",
        "get_product_details",
        "get_order_status",
        "list_my_orders",
        "create_support_ticket",
        "get_ticket_status",
        "request_refund",
    }

    assert {support_tool.name for support_tool in tools} == expected_names
    for support_tool in tools:
        schema = support_tool.args_schema.model_json_schema()
        assert "customer_id" not in schema["properties"]
        assert "trusted_customer_id" not in schema["properties"]


def test_product_details_only_returns_active_products(db_session):
    product = Product(
        name="Active Headphones",
        description="A product description.",
        category="Audio",
        price="2000.00",
        stock=8,
        active=True,
    )
    inactive = Product(
        name="Inactive Headphones",
        description="Not for sale.",
        category="Audio",
        price="1500.00",
        stock=0,
        active=False,
    )
    db_session.add_all([product, inactive])
    db_session.commit()

    tool = get_tool(db_session, "get_product_details")
    active_result = json.loads(tool.invoke({"product_id": product.id}))
    inactive_result = json.loads(tool.invoke({"product_id": inactive.id}))

    assert active_result["found"] is True
    assert active_result["product"]["name"] == "Active Headphones"
    assert inactive_result["found"] is False


def test_order_tools_only_return_authenticated_customers_orders(db_session):
    first = Customer(
        name="First Customer",
        email="first-tool@example.com",
        password_hash="hash",
    )
    second = Customer(
        name="Second Customer",
        email="second-tool@example.com",
        password_hash="hash",
    )
    product = Product(
        name="Order Product",
        description="Order test product.",
        category="Testing",
        price="99.00",
        stock=2,
    )
    db_session.add_all([first, second, product])
    db_session.flush()
    first_order = Order(customer_id=first.id, status="shipped")
    second_order = Order(customer_id=second.id, status="delivered")
    first_order.items.append(
        OrderItem(product_id=product.id, quantity=1, unit_price=product.price)
    )
    second_order.items.append(
        OrderItem(product_id=product.id, quantity=1, unit_price=product.price)
    )
    db_session.add_all([first_order, second_order])
    db_session.commit()

    one_order = json.loads(
        get_tool(
            db_session, "get_order_status", trusted_customer_id=first.id
        ).invoke({"order_id": second_order.id})
    )
    my_orders = json.loads(
        get_tool(
            db_session, "list_my_orders", trusted_customer_id=first.id
        ).invoke({"limit": 10})
    )
    unauthenticated = json.loads(
        get_tool(db_session, "list_my_orders").invoke({"limit": 10})
    )

    assert one_order["found"] is False
    assert [item["id"] for item in my_orders["orders"]] == [first_order.id]
    assert "error" in unauthenticated


def test_ticket_status_is_owner_scoped(db_session):
    owner = Customer(
        name="Ticket Owner",
        email="ticket-owner-tool@example.com",
        password_hash="hash",
    )
    other = Customer(
        name="Other Customer",
        email="ticket-other-tool@example.com",
        password_hash="hash",
    )
    db_session.add_all([owner, other])
    db_session.flush()
    ticket = SupportTicket(
        customer_id=owner.id,
        subject="Order help",
        description="Please help with my order.",
        status="in_progress",
    )
    db_session.add(ticket)
    db_session.commit()

    own_result = json.loads(
        get_tool(
            db_session, "get_ticket_status", trusted_customer_id=owner.id
        ).invoke({"ticket_id": ticket.id})
    )
    other_result = json.loads(
        get_tool(
            db_session, "get_ticket_status", trusted_customer_id=other.id
        ).invoke({"ticket_id": ticket.id})
    )

    assert own_result["found"] is True
    assert own_result["ticket"]["status"] == "in_progress"
    assert other_result["found"] is False


def test_refund_tool_creates_tracked_request_only_for_eligible_owned_order(
    db_session,
):
    owner = Customer(
        name="Refund Owner",
        email="refund-owner-tool@example.com",
        password_hash="hash",
    )
    other = Customer(
        name="Other Refund Customer",
        email="refund-other-tool@example.com",
        password_hash="hash",
    )
    db_session.add_all([owner, other])
    db_session.flush()
    delivered = Order(
        customer_id=owner.id,
        status="delivered",
        delivered_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    processing = Order(customer_id=owner.id, status="processing")
    db_session.add_all([delivered, processing])
    db_session.commit()

    owner_tool = get_tool(
        db_session, "request_refund", trusted_customer_id=owner.id
    )
    other_tool = get_tool(
        db_session, "request_refund", trusted_customer_id=other.id
    )
    unauthorized = json.loads(
        other_tool.invoke(
            {
                "order_id": delivered.id,
                "request_type": "refund",
                "reason": "The item arrived damaged.",
            }
        )
    )
    ineligible = json.loads(
        owner_tool.invoke(
            {
                "order_id": processing.id,
                "request_type": "return",
                "reason": "I want to return this item.",
            }
        )
    )
    created = json.loads(
        owner_tool.invoke(
            {
                "order_id": delivered.id,
                "request_type": "refund",
                "reason": "The item arrived damaged.",
            }
        )
    )
    duplicate = json.loads(
        owner_tool.invoke(
            {
                "order_id": delivered.id,
                "request_type": "refund",
                "reason": "The item arrived damaged.",
            }
        )
    )

    assert unauthorized["success"] is False
    assert ineligible["success"] is False
    assert created["success"] is True
    assert created["status"] == "pending"
    assert duplicate["success"] is False
    assert (
        db_session.scalar(
            select(RefundRequest).where(
                RefundRequest.id == created["request_id"]
            )
        ).status
        == "pending"
    )

def test_ticket_tool_requires_trusted_customer_id(db_session):
    """Ticket creation must require an authenticated customer."""

    ticket_tool = get_ticket_tool(db_session)

    result = json.loads(
        ticket_tool.invoke({
            "subject": "Delivery issue",
            "description": "My order has not been delivered.",
        })
    )

    assert result["success"] is False
    assert "error" in result
    assert "authenticated customer" in result["error"].lower()

def test_ticket_tool_creates_ticket_for_authenticated_customer(
    db_session,
):
    """An authenticated customer should be able to create a ticket."""

    # Arrange: create a customer in the isolated test database.
    customer = Customer(
        name="Test Customer",
        email="test.customer@example.com",
        password_hash="test-password-hash",
    )

    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    # Use the actual ID generated by the database.
    ticket_tool = get_ticket_tool(
        db_session,
        trusted_customer_id=customer.id,
    )

    # Act: create the support ticket.
    result = json.loads(
        ticket_tool.invoke({
            "subject": "Delivery issue",
            "description": "My order has not been delivered.",
        })
    )

    # Assert: verify the ticket was created successfully.
    assert result["success"] is True
    assert isinstance(result["ticket_id"], int)
    assert result["ticket_id"] > 0
    assert result["subject"] == "Delivery issue"
    assert result["status"] == "open"

@pytest.mark.parametrize(
    ("subject", "description"),
    [
        ("Hi", "My order has not been delivered."),
        ("Delivery issue", "Oops"),
        ("", "My order has not been delivered."),
        ("Delivery issue", ""),
    ],
)
def test_ticket_tool_rejects_invalid_input(
    db_session,
    subject,
    description,
):
    """Reject invalid ticket subjects and descriptions."""

    ticket_tool = get_ticket_tool(
        db_session,
        trusted_customer_id=1,
    )

    result = json.loads(
        ticket_tool.invoke({
            "subject": subject,
            "description": description,
        })
    )

    assert result["success"] is False
    assert "error" in result