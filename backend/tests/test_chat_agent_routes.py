
def test_chat_agent_rejects_unauthenticated_request(client):
    """The tool agent must require customer authentication."""

    response = client.post(
        "/api/chat/agent",
        json={"message": "Where is my order?"},
    )

    assert response.status_code == 401


def test_chat_agent_passes_authenticated_customer_to_service(
    client,
    monkeypatch,
):
    """Pass the verified customer ID to the tool agent service."""

    from app.core.security import get_current_customer

    class FakeCustomer:
        id = 123
        name = "Test Customer"
        email = "test@example.com"

    def override_get_current_customer():
        return FakeCustomer()

    client.app.dependency_overrides[get_current_customer] = (
        override_get_current_customer
    )

    def fake_answer_with_tools(
        message,
        db,
        trusted_customer_id=None,
    ):
        assert message == "Where is my order?"
        assert db is not None
        assert trusted_customer_id == 123

        return "Please provide your order ID."

    monkeypatch.setattr(
        "app.api.chat_routes.answer_with_tools",
        fake_answer_with_tools,
    )

    try:
        response = client.post(
            "/api/chat/agent",
            json={"message": "Where is my order?"},
        )
    finally:
        client.app.dependency_overrides.pop(
            get_current_customer,
            None,
        )

    assert response.status_code == 200
    assert response.json()["answer"] == "Please provide your order ID."


def test_chat_agent_handles_service_failure(client, monkeypatch):
    """Return a safe error response when the service fails."""

    from app.core.security import get_current_customer

    class FakeCustomer:
        id = 123
        name = "Test Customer"
        email = "test@example.com"

    client.app.dependency_overrides[get_current_customer] = (
        lambda: FakeCustomer()
    )

    def fail_to_answer(*args, **kwargs):
        raise RuntimeError("Simulated provider failure")

    monkeypatch.setattr(
        "app.api.chat_routes.answer_with_tools",
        fail_to_answer,
    )

    try:
        response = client.post(
            "/api/chat/agent",
            json={"message": "Find laptops"},
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
