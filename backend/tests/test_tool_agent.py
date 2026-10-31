
from app.core.security import get_current_customer
import json
from types import SimpleNamespace

from app.services import tool_agent_service

class FakeCustomer:
    id = 123
    name = "Test Customer"
    email = "test@example.com"


def override_get_current_customer():
    return FakeCustomer()


def test_agent_endpoint_returns_answer(client, monkeypatch):
    """Test product-agent response with an authenticated customer."""

    client.app.dependency_overrides[get_current_customer] = (
        override_get_current_customer
    )

    def fake_answer(
        message,
        db,
        trusted_customer_id=None,
    ):
        assert message == "Find me a product"
        assert db is not None
        assert trusted_customer_id == 123
        return "I found two products matching your search."

    monkeypatch.setattr(
        "app.api.chat_routes.answer_with_tools",
        fake_answer,
    )

    try:
        response = client.post(
            "/api/chat/agent",
            json={"message": "Find me a product"},
        )
    finally:
        client.app.dependency_overrides.pop(
            get_current_customer,
            None,
        )

    assert response.status_code == 200
    assert response.json()["answer"] == (
        "I found two products matching your search."
    )


def test_agent_endpoint_rejects_empty_message(
    client,
):
    """Validate the request schema after authentication."""

    client.app.dependency_overrides[get_current_customer] = (
        override_get_current_customer
    )

    try:
        response = client.post(
            "/api/chat/agent",
            json={"message": "   "},
        )
    finally:
        client.app.dependency_overrides.pop(
            get_current_customer,
            None,
        )

    assert response.status_code == 422


def test_agent_endpoint_handles_runtime_error(
    client,
    monkeypatch,
):
    """Return a safe response if the tool service fails."""

    client.app.dependency_overrides[get_current_customer] = (
        override_get_current_customer
    )

    def fail_to_answer(
        message,
        db,
        trusted_customer_id=None,
    ):
        raise RuntimeError("Simulated agent failure")

    monkeypatch.setattr(
        "app.api.chat_routes.answer_with_tools",
        fail_to_answer,
    )

    try:
        response = client.post(
            "/api/chat/agent",
            json={"message": "Find me a product"},
        )
    finally:
        client.app.dependency_overrides.pop(
            get_current_customer,
            None,
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The AI service is currently unavailable."
    )


def test_agent_executes_ticket_creation_tool(
    db_session,
    monkeypatch,
):
    """The agent should execute a requested ticket-creation tool."""

    class FakeTool:
        name = "create_support_ticket"

        def invoke(self, args):
            assert args["subject"] == "Delivery issue"
            assert args["description"] == (
                "My order has not been delivered."
            )

            return json.dumps({
                "success": True,
                "ticket_id": 42,
                "subject": "Delivery issue",
                "status": "open",
                "message": "Support ticket #42 was created successfully.",
            })


    class FakeLLM:
        def __init__(self, *args, **kwargs):
            self.invocation_count = 0

        def bind_tools(self, tools):
            assert any(
                support_tool.name == "create_support_ticket"
                for support_tool in tools
            )
            return self

        def invoke(self, messages):
            self.invocation_count += 1

            # First call: request ticket creation.
            if self.invocation_count == 1:
                return SimpleNamespace(
                    tool_calls=[{
                        "name": "create_support_ticket",
                        "args": {
                            "subject": "Delivery issue",
                            "description": (
                                "My order has not been delivered."
                            ),
                        },
                    }],
                    content="",
                )

            # Second call: return the final customer-facing answer.
            return SimpleNamespace(
                content="Support ticket #42 was created successfully."
            )

    monkeypatch.setattr(
        tool_agent_service,
        "GROQ_API_KEY",
        "test-api-key",
    )
    monkeypatch.setattr(
        tool_agent_service,
        "create_support_tools",
        lambda db, trusted_customer_id=None: [FakeTool()],
    )
    monkeypatch.setattr(
        tool_agent_service,
        "create_groq_chat_model",
        lambda **kwargs: FakeLLM(),
    )

    answer = tool_agent_service.answer_with_tools(
        message="Please create a ticket for my delivery issue.",
        db=db_session,
        trusted_customer_id=123,
    )

    assert answer == "Support ticket #42 was created successfully."


def test_agent_does_not_claim_ticket_created_when_tool_fails(
    db_session,
    monkeypatch,
):
    """The final response must reflect a failed ticket creation."""

    class FakeTool:
        name = "create_support_ticket"

        def invoke(self, args):
            return json.dumps({
                "success": False,
                "error": "Ticket creation requires an authenticated customer.",
            })

    class FakeLLM:
        def __init__(self, *args, **kwargs):
            self.invocation_count = 0

        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            self.invocation_count += 1

            if self.invocation_count == 1:
                return SimpleNamespace(
                    tool_calls=[{
                        "name": "create_support_ticket",
                        "args": {
                            "subject": "Delivery issue",
                            "description": (
                                "My order has not been delivered."
                            ),
                        },
                    }],
                    content="",
                )

            # Simulate an appropriate response to the failed tool result.
            return SimpleNamespace(
                content=(
                    "I couldn't create the ticket because authentication "
                    "is required."
                )
            )

    monkeypatch.setattr(
        tool_agent_service,
        "GROQ_API_KEY",
        "test-api-key",
    )
    monkeypatch.setattr(
        tool_agent_service,
        "create_support_tools",
        lambda db, trusted_customer_id=None: [FakeTool()],
    )
    monkeypatch.setattr(
        tool_agent_service,
        "create_groq_chat_model",
        lambda **kwargs: FakeLLM(),
    )

    answer = tool_agent_service.answer_with_tools(
        message="Please create a ticket for my delivery issue.",
        db=db_session,
        trusted_customer_id=None,
    )

    assert "couldn't create" in answer.lower()
    assert "authentication" in answer.lower()
    assert "successfully created" not in answer.lower()


def test_agent_returns_validated_product_cards_for_support_graph(
    db_session,
    monkeypatch,
):
    class FakeTool:
        name = "search_products"

        def invoke(self, args):
            return json.dumps({
                "count": 1,
                "products": [
                    {
                        "id": 7,
                        "name": "Wireless Headphones",
                        "description": "Over-ear audio.",
                        "category": "Audio",
                        "price": "2500.00",
                        "stock": 3,
                    },
                    {
                        "id": "invalid",
                        "name": "Malformed result",
                        "price": "0",
                        "stock": 1,
                    },
                ],
            })

    class FakeLLM:
        def __init__(self):
            self.invocation_count = 0

        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            self.invocation_count += 1
            if self.invocation_count == 1:
                return SimpleNamespace(
                    tool_calls=[{
                        "name": "search_products",
                        "args": {"query": "wireless headphones"},
                    }],
                    content="",
                )
            return SimpleNamespace(content="I found one matching product.")

    monkeypatch.setattr(tool_agent_service, "GROQ_API_KEY", "test-api-key")
    monkeypatch.setattr(
        tool_agent_service,
        "create_support_tools",
        lambda db, trusted_customer_id=None: [FakeTool()],
    )
    monkeypatch.setattr(
        tool_agent_service,
        "create_groq_chat_model",
        lambda **kwargs: FakeLLM(),
    )

    result = tool_agent_service.answer_with_tools(
        message="Find wireless headphones.",
        db=db_session,
        trusted_customer_id=123,
        include_products=True,
    )

    assert result == {
        "answer": "I found one matching product.",
        "products": [
            {
                "id": 7,
                "name": "Wireless Headphones",
                "description": "Over-ear audio.",
                "category": "Audio",
                "price": "2500.00",
                "stock": 3,
            }
        ],
    }


def test_catalogue_search_fallback_returns_products_for_mixed_request(
    db_session,
    monkeypatch,
):
    from app.models import Product

    product = Product(
        name="Bluetooth Headphones",
        description="Wireless over-ear headphones with cushioned ear cups.",
        category="Audio",
        price="1999.00",
        stock=7,
        active=True,
    )
    db_session.add(product)
    db_session.commit()

    class FakeLLM:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            return SimpleNamespace(tool_calls=[], content="No products found.")

    monkeypatch.setattr(tool_agent_service, "GROQ_API_KEY", "test-api-key")
    monkeypatch.setattr(
        tool_agent_service,
        "create_groq_chat_model",
        lambda **kwargs: FakeLLM(),
    )

    result = tool_agent_service.answer_with_tools(
        message=(
            "What is the return window? Also show wireless headphones "
            "under ₹3000."
        ),
        db=db_session,
        trusted_customer_id=123,
        include_products=True,
    )

    assert result["answer"] == "Here are matching products from the live catalogue."
    assert [item["name"] for item in result["products"]] == [
        "Bluetooth Headphones"
    ]
