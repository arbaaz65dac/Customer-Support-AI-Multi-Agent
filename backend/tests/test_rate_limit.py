from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.rate_limit import (
    InMemoryRateLimiter,
    auth_rate_limiter,
    chat_rate_limiter,
)
from app.core.security import get_current_customer


def test_fixed_window_limit_resets_after_window():
    now = [100.0]
    limiter = InMemoryRateLimiter(
        max_requests=2,
        window_seconds=30,
        clock=lambda: now[0],
    )
    limiter.check("test")
    limiter.check("test")

    with pytest.raises(HTTPException) as exc_info:
        limiter.check("test")
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "30"

    now[0] += 30
    limiter.check("test")


def test_signup_rate_limit_returns_retry_after(client, monkeypatch):
    monkeypatch.setattr(auth_rate_limiter, "max_requests", 1)
    response = client.post(
        "/api/customers",
        json={
            "name": "Rate Limited Customer",
            "email": "rate-limit-signup@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 201

    limited = client.post(
        "/api/customers",
        json={
            "name": "Second Customer",
            "email": "rate-limit-second@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert limited.status_code == 429
    assert limited.json()["detail"] == (
        "Too many requests. Please try again later."
    )
    assert limited.headers["Retry-After"].isdigit()


def test_login_rate_limit_returns_retry_after(client, monkeypatch):
    monkeypatch.setattr(auth_rate_limiter, "max_requests", 1)
    login_payload = {
        "email": "unknown@example.com",
        "password": "not-the-password",
    }
    assert client.post("/api/auth/login", json=login_payload).status_code == 401

    limited = client.post("/api/auth/login", json=login_payload)
    assert limited.status_code == 429
    assert limited.headers["Retry-After"].isdigit()


def test_chat_rate_limit_is_per_user_and_resets(client, monkeypatch):
    monkeypatch.setattr(chat_rate_limiter, "max_requests", 1)
    now = [50.0]
    monkeypatch.setattr(chat_rate_limiter, "_clock", lambda: now[0])
    customer = SimpleNamespace(id=71)
    client.app.dependency_overrides[get_current_customer] = lambda: customer
    monkeypatch.setattr(
        "app.api.support_graph_routes.support_graph.invoke",
        lambda state, context, config: {
            "answer": "Allowed response",
            "intent": "general_question",
            "selected_agent": "general",
        },
    )

    def ask():
        return client.post(
            "/api/support/ask",
            json={"question": "Hello"},
        )

    assert ask().status_code == 200
    customer.id = 72
    assert ask().status_code == 200
    customer.id = 71
    limited = ask()
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"

    now[0] += 60
    assert ask().status_code == 200
