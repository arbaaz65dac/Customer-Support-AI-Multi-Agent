from types import SimpleNamespace

from app.core.security import get_current_customer
from app.core.config import FRONTEND_ORIGIN


def test_health_endpoint_returns_healthy_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "message": "Customer Support AI backend is running!",
    }
    assert response.headers["X-Request-ID"]


def test_provider_failure_has_safe_error_and_request_id(
    client,
    monkeypatch,
    caplog,
):
    client.app.dependency_overrides[get_current_customer] = (
        lambda: SimpleNamespace(id=501, role="customer")
    )
    monkeypatch.setattr(
        "app.api.support_graph_routes.support_graph.invoke",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("sensitive provider message")
        ),
    )

    response = client.post(
        "/api/support/ask",
        json={"question": "Where is my order?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The support assistant is currently unavailable."
    )
    assert response.headers["X-Request-ID"]
    assert "sensitive provider message" not in response.text
    provider_logs = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "provider_error"
    ]
    assert provider_logs
    assert provider_logs[0].request_id == response.headers["X-Request-ID"]
    assert "sensitive provider message" not in caplog.text


def test_health_endpoint_cors_allows_only_configured_frontend(client):
    allowed_response = client.options(
        "/health",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    disallowed_response = client.options(
        "/health",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed_response.headers["access-control-allow-origin"] == (
        FRONTEND_ORIGIN
    )
    assert "access-control-allow-origin" not in disallowed_response.headers
