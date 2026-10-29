
import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_customer
from app.main import app


class FakeCustomer:
    """Simulated authenticated customer for endpoint tests."""

    id = 123
    name = "Test Customer"
    email = "test@example.com"


def override_get_current_customer():
    return FakeCustomer()


@pytest.fixture
def authenticated_client():
    """Create a client with a test-only authenticated customer."""

    original_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_current_customer] = (
        override_get_current_customer
    )

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def unauthenticated_client():
    """Create a client without the test authentication override."""

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides.pop(get_current_customer, None)

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def test_support_graph_endpoint_returns_graph_result(
    authenticated_client,
    monkeypatch,
):
    """Test the endpoint without invoking the real LLM."""

    def fake_invoke(state, context):
        assert state["question"] == "What is the refund policy?"
        assert "db" in context
        assert context["customer_id"] == 123

        return {
            "question": state["question"],
            "intent": "policy_question",
            "selected_agent": "knowledge",
            "answer": "The policy does not specify a refund timeline.",
            "sources": ["returns_refunds_policy.md"],
            "retrieved_chunks": 2,
        }

    monkeypatch.setattr(
        "app.api.support_graph_routes.support_graph.invoke",
        fake_invoke,
    )

    response = authenticated_client.post(
        "/api/support/ask",
        json={"question": "What is the refund policy?"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["intent"] == "policy_question"
    assert data["selected_agent"] == "knowledge"
    assert data["answer"] == (
        "The policy does not specify a refund timeline."
    )
    assert data["sources"] == ["returns_refunds_policy.md"]
    assert data["retrieved_chunks"] == 2


def test_support_graph_endpoint_rejects_missing_question(
    authenticated_client,
):
    response = authenticated_client.post(
        "/api/support/ask",
        json={},
    )

    assert response.status_code == 422


def test_support_graph_endpoint_rejects_blank_question(
    authenticated_client,
):
    response = authenticated_client.post(
        "/api/support/ask",
        json={"question": "   "},
    )

    assert response.status_code == 422


def test_support_graph_endpoint_handles_runtime_failure(
    authenticated_client,
    monkeypatch,
):
    def fail_invoke(state, context):
        raise RuntimeError("Simulated provider failure")

    monkeypatch.setattr(
        "app.api.support_graph_routes.support_graph.invoke",
        fail_invoke,
    )

    response = authenticated_client.post(
        "/api/support/ask",
        json={"question": "What is the refund policy?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The support assistant is currently unavailable."
    )


def test_support_graph_endpoint_rejects_unauthenticated_request(
    unauthenticated_client,
):
    response = unauthenticated_client.post(
        "/api/support/ask",
        json={"question": "What is the refund policy?"},
    )

    assert response.status_code == 401
