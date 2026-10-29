
from app.core.security import get_current_customer


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
