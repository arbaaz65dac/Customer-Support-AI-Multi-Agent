
import json

import pytest

from app.services.agent_tools import create_support_tools


def get_order_tool(db_session, trusted_customer_id=None):
    """Get the order lookup tool with an optional trusted customer ID."""
    tools = create_support_tools(
        db_session,
        trusted_customer_id=trusted_customer_id,
    )

    return next(
        tool
        for tool in tools
        if tool.name == "lookup_order_status"
    )


def get_product_tool(db_session):
    """Get the product search tool."""
    tools = create_support_tools(db_session)

    return next(
        tool
        for tool in tools
        if tool.name == "search_product_catalog"
    )


def test_product_tool_rejects_empty_query(db_session):
    product_tool = get_product_tool(db_session)

    result = json.loads(
        product_tool.invoke({"query": "   "})
    )

    assert "error" in result
    assert "empty" in result["error"].lower()


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
    assert "positive integers" in result["error"]


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
