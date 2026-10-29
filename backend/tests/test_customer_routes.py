
from app.core.security import get_current_customer


class FakeCustomer:
    def __init__(self, customer_id=123):
        self.id = customer_id
        self.name = "Test Customer"
        self.email = "test@example.com"


def test_customer_profile_requires_authentication(client):
    """Reject requests without a valid authentication token."""

    response = client.get("/api/customers/123")

    assert response.status_code == 401


def test_customer_can_access_own_profile(client):
    """Allow an authenticated customer to access their own profile."""

    from app.models import Customer

    db = next(
        client.app.dependency_overrides[
            __import__("app.database", fromlist=["get_db"]).get_db
        ]()
    )

    customer = Customer(
        name="Test Customer",
        email="test@example.com",
        password_hash="test-hash",
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)
    customer_id = customer.id
    db.close()

    client.app.dependency_overrides[get_current_customer] = (
        lambda: FakeCustomer(customer_id)
    )

    try:
        response = client.get(f"/api/customers/{customer_id}")
    finally:
        client.app.dependency_overrides.pop(
            get_current_customer,
            None,
        )

    assert response.status_code == 200
    assert response.json()["id"] == customer_id
    assert response.json()["email"] == "test@example.com"


def test_customer_cannot_access_another_profile(client):
    """Prevent access to another customer's profile."""

    client.app.dependency_overrides[get_current_customer] = (
        lambda: FakeCustomer(123)
    )

    try:
        response = client.get("/api/customers/456")
    finally:
        client.app.dependency_overrides.pop(
            get_current_customer,
            None,
        )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You cannot access another customer's profile."
    )
