
from app.core.security import get_current_customer
from app.database import get_db
from app.main import app
from app.models import Customer


def create_test_customer(client):
    response = client.post(
        "/api/customers",
        json={
            "name": "Dashboard Test Customer",
            "email": "dashboard-test@example.com",
            "password": "DemoPassword123!",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def login_test_customer(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "dashboard-test@example.com",
            "password": "DemoPassword123!",
        },
    )

    assert response.status_code == 200
    return response.json()["access_token"]


def create_test_admin():
    """Create an administrator in the test database."""

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    admin = Customer(
        name="Dashboard Test Admin",
        email="dashboard-admin@example.com",
        password_hash="test-password-hash",
        role="admin",
    )

    try:
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
    finally:
        db_generator.close()


def test_dashboard_requires_authentication(client):
    """Unauthenticated users cannot access the admin dashboard."""

    response = client.get("/api/admin/dashboard")

    assert response.status_code == 401


def test_customer_cannot_access_admin_dashboard(client):
    """Ordinary customers cannot access dashboard statistics."""

    create_test_customer(client)
    token = login_test_customer(client)

    response = client.get(
        "/api/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access required."


def test_admin_dashboard_returns_ticket_counts(client):
    """Dashboard counts reflect tickets stored in the database."""

    create_test_customer(client)
    token = login_test_customer(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create three tickets, initially all open.
    for subject in [
        "Delivery enquiry",
        "Refund enquiry",
        "Product enquiry",
    ]:
        response = client.post(
            "/api/support-tickets",
            headers=headers,
            json={
                "subject": subject,
                "description": (
                    "Please help me with this customer support issue."
                ),
            },
        )
        assert response.status_code == 201

    # Change one ticket to in_progress and another to resolved.
    tickets_response = client.get(
        "/api/support-tickets",
        headers=headers,
    )
    assert tickets_response.status_code == 200

    tickets = tickets_response.json()

    admin = create_test_admin()
    app.dependency_overrides[get_current_customer] = lambda: admin

    try:
        for ticket, new_status in [
            (tickets[0], "in_progress"),
            (tickets[1], "resolved"),
        ]:
            update_response = client.patch(
                f"/api/support-tickets/{ticket['id']}/status",
                json={"status": new_status},
            )
            assert update_response.status_code == 200

        dashboard_response = client.get("/api/admin/dashboard")
    finally:
        app.dependency_overrides.pop(get_current_customer, None)

    assert dashboard_response.status_code == 200
    assert dashboard_response.json() == {
        "total_tickets": 3,
        "open_tickets": 1,
        "in_progress_tickets": 1,
        "resolved_tickets": 1,
        "total_customers": 1,
        "total_orders": 0,
        "revenue": 0.0,
    }


def test_empty_dashboard_returns_zero_counts(client):
    """An empty database returns zero for every ticket count."""

    admin = create_test_admin()
    app.dependency_overrides[get_current_customer] = lambda: admin

    try:
        response = client.get("/api/admin/dashboard")
    finally:
        app.dependency_overrides.pop(get_current_customer, None)

    assert response.status_code == 200
    assert response.json() == {
        "total_tickets": 0,
        "open_tickets": 0,
        "in_progress_tickets": 0,
        "resolved_tickets": 0,
        "total_customers": 0,
        "total_orders": 0,
        "revenue": 0.0,
    }
