import json

from app.services.agent_tools import create_support_tools


def test_product_tool_rejects_empty_query(db_session):
    tools = create_support_tools(db_session)
    product_tool = next(
        tool for tool in tools
        if tool.name == "search_product_catalog"
    )

    result = json.loads(
        product_tool.invoke({"query": "   "})
    )

    assert "error" in result
    assert "empty" in result["error"].lower()


def test_product_tool_rejects_excessive_query_length(db_session):
    tools = create_support_tools(db_session)
    product_tool = next(
        tool for tool in tools
        if tool.name == "search_product_catalog"
    )

    result = json.loads(
        product_tool.invoke({"query": "x" * 101})
    )

    assert "error" in result
    assert "100 characters" in result["error"]


def test_product_tool_rejects_invalid_max_price(db_session):
    tools = create_support_tools(db_session)
    product_tool = next(
        tool for tool in tools
        if tool.name == "search_product_catalog"
    )

    result = json.loads(
        product_tool.invoke({
            "query": "mouse",
            "max_price": -10,
        })
    )

    assert "error" in result
    assert "Maximum price" in result["error"]


def test_order_tool_rejects_non_positive_ids(db_session):
    tools = create_support_tools(db_session)
    order_tool = next(
        tool for tool in tools
        if tool.name == "lookup_order_status"
    )

    result = json.loads(
        order_tool.invoke({
            "order_id": 0,
            "customer_id": 1,
        })
    )

    assert "error" in result
    assert "positive integers" in result["error"]