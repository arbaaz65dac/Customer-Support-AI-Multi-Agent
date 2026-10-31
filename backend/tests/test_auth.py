
import jwt
import pytest

from app.core.config import JWT_ALGORITHM, JWT_SECRET_KEY
from app.models import Customer
from app.services.auth_service import (
    create_access_token,
    decode_access_token,
)



@pytest.fixture
def registered_customer(client):
    """Register a customer through the existing API."""

    response = client.post(
        "/api/customers",
        json={
            "name": "Test Customer",
            "email": "auth-test@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert response.status_code == 201
    return response.json()


def test_customer_registration_does_not_return_password_hash(
    registered_customer,
):
    assert registered_customer["id"] > 0
    assert registered_customer["email"] == "auth-test@example.com"
    assert "password_hash" not in registered_customer
    assert "password" not in registered_customer


def test_login_returns_access_token(client, registered_customer):
    response = client.post(
        "/api/auth/login",
        json={
            "email": registered_customer["email"],
            "password": "CorrectPassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert data["access_token"]
    assert data["expires_in"] > 0
    assert data["role"] == "customer"

    assert (
        decode_access_token(data["access_token"])
        == registered_customer["id"]
    )


def test_login_rejects_incorrect_password(client, registered_customer):
    response = client.post(
        "/api/auth/login",
        json={
            "email": registered_customer["email"],
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "SomePassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_decode_access_token_rejects_invalid_token():
    assert decode_access_token("not-a-valid-token") is None


def test_decode_access_token_rejects_expired_token(
    registered_customer,
):
    # Use an already-expired token signed with the configured secret.
    from datetime import datetime, timedelta, timezone

    expired_payload = {
        "sub": str(registered_customer["id"]),
        "iat": datetime.now(timezone.utc) - timedelta(minutes=10),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }

    expired_token = jwt.encode(
        expired_payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    assert decode_access_token(expired_token) is None


def test_support_endpoint_rejects_request_without_token(client):
    response = client.post(
        "/api/support/ask",
        json={"question": "Where is my order?"},
    )

    assert response.status_code == 401


def test_customer_profile_includes_authenticated_role(
    client,
    registered_customer,
):
    login = client.post(
        "/api/auth/login",
        json={
            "email": registered_customer["email"],
            "password": "CorrectPassword123!",
        },
    )
    profile = client.get(
        f"/api/customers/{registered_customer['id']}",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["role"] == "customer"


def test_admin_login_returns_admin_role(client):
    from pwdlib import PasswordHash

    from app.database import get_db

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    admin = Customer(
        name="Role Test Admin",
        email="role-test-admin@example.com",
        password_hash=PasswordHash.recommended().hash("RoleTestPassword123!"),
        role="admin",
    )
    db.add(admin)
    db.commit()
    db_generator.close()

    response = client.post(
        "/api/auth/login",
        json={
            "email": "role-test-admin@example.com",
            "password": "RoleTestPassword123!",
        },
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_support_endpoint_accepts_valid_customer_token(
    client,
    registered_customer,
    monkeypatch,
):
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": registered_customer["email"],
            "password": "CorrectPassword123!",
        },
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    def fake_invoke(state, context, config):
        assert context["customer_id"] == registered_customer["id"]
        assert config["recursion_limit"] == 6

        return {
            "question": state["question"],
            "intent": "general_question",
            "selected_agent": "general",
            "answer": "Hello! How can I help?",
            "sources": [],
            "retrieved_chunks": 0,
        }

    monkeypatch.setattr(
        "app.api.support_graph_routes.support_graph.invoke",
        fake_invoke,
    )

    response = client.post(
        "/api/support/ask",
        json={"question": "Hello"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Hello! How can I help?"


from app.main import app

def test_support_endpoint_rejects_invalid_bearer_token(client):
    response = client.post(
        "/api/support/ask",
        json={"question": "Where is my order?"},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401

def test_public_registration_cannot_assign_admin_role(client):
    """Public registration must never grant administrator privileges."""

    response = client.post(
        "/api/customers",
        json={
            "name": "Attempted Admin",
            "email": "attempted-admin@example.com",
            "password": "SecurePassword123!",
            "role": "admin",
        },
    )

    assert response.status_code == 201

    # The public response must not expose the password hash.
    assert "password_hash" not in response.json()

    # Check the stored role directly in the test database.
    from sqlalchemy import select

    from app.database import get_db
    from app.models import Customer

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    try:
        customer = db.scalar(
            select(Customer).where(
                Customer.email == "attempted-admin@example.com"
            )
        )

        assert customer is not None
        assert customer.role == "customer"
    finally:
        db_generator.close()