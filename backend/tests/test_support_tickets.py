
from app.core.security import get_current_customer
from app.database import get_db
from app.main import app
from app.models import Customer


def create_test_customer(client):
    """Register a customer and return their ID."""
    response = client.post(
        "/api/customers",
        json={
            "name": "Ticket Test Customer",
            "email": "ticket-test@example.com",
            "password": "DemoPassword123!",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def login_test_customer(client):
    """Log in and return the JWT access token."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "ticket-test@example.com",
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
        name="Ticket Test Admin",
        email="ticket-admin-test@example.com",
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


def test_create_and_list_support_tickets(client):
    """An authenticated customer can create and list their tickets."""
    customer_id = create_test_customer(client)
    token = login_test_customer(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/support-tickets",
        headers=headers,
        json={
            "subject": "Delivery enquiry",
            "description": "Please provide an update on my delivery.",
        },
    )

    assert create_response.status_code == 201

    ticket = create_response.json()
    assert ticket["status"] == "open"
    assert ticket["customer_id"] == customer_id

    list_response = client.get(
        "/api/support-tickets",
        headers=headers,
    )

    assert list_response.status_code == 200

    tickets = list_response.json()
    assert len(tickets) == 1
    assert tickets[0]["id"] == ticket["id"]
    assert tickets[0]["customer_id"] == customer_id


def test_create_ticket_rejects_unauthenticated_request(client):
    """Ticket creation requires a valid bearer token."""
    response = client.post(
        "/api/support-tickets",
        json={
            "subject": "Delivery enquiry",
            "description": "Please provide an update on my delivery.",
        },
    )

    assert response.status_code == 401


def test_list_tickets_rejects_unauthenticated_request(client):
    """Customer ticket listing requires authentication."""
    response = client.get("/api/support-tickets")

    assert response.status_code == 401


def test_customer_cannot_choose_ticket_owner(client):
    """A request cannot assign a ticket to a different customer."""
    customer_id = create_test_customer(client)
    token = login_test_customer(client)

    response = client.post(
        "/api/support-tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "customer_id": 99999,
            "subject": "Delivery enquiry",
            "description": "Please provide an update on my delivery.",
        },
    )

    # customer_id is not part of the updated request schema.
    assert response.status_code == 201
    assert response.json()["customer_id"] == customer_id


def test_admin_ticket_listing_rejects_unauthenticated_request(client):
    """The admin ticket listing requires authentication."""

    response = client.get("/api/support-tickets/admin/all")

    assert response.status_code == 401


def test_customer_cannot_access_admin_ticket_listing(client):
    """An ordinary customer cannot view all customers' tickets."""

    create_test_customer(client)
    token = login_test_customer(client)

    response = client.get(
        "/api/support-tickets/admin/all",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access required."


def test_admin_can_list_all_support_tickets(client):
    """An administrator can view tickets across customers."""

    customer_id = create_test_customer(client)
    token = login_test_customer(client)

    # Create a ticket belonging to the ordinary customer.
    ticket_response = client.post(
        "/api/support-tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "subject": "Delivery enquiry",
            "description": "Please provide an update on my delivery.",
        },
    )

    assert ticket_response.status_code == 201
    expected_ticket_id = ticket_response.json()["id"]

    # Create an administrator and temporarily authenticate the request
    # as that administrator.
    admin = create_test_admin()
    app.dependency_overrides[get_current_customer] = lambda: admin

    try:
        response = client.get("/api/support-tickets/admin/all")
    finally:
        app.dependency_overrides.pop(get_current_customer, None)

    assert response.status_code == 200

    tickets = response.json()
    assert len(tickets) == 1
    assert tickets[0]["id"] == expected_ticket_id
    assert tickets[0]["customer_id"] == customer_id

def test_admin_can_update_ticket_status(client):
    """An administrator can move a ticket to in_progress."""

    create_test_customer(client)
    token = login_test_customer(client)

    ticket_response = client.post(
        "/api/support-tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "subject": "Delivery enquiry",
            "description": "Please provide an update on my delivery.",
        },
    )

    assert ticket_response.status_code == 201
    ticket_id = ticket_response.json()["id"]

    admin = create_test_admin()
    app.dependency_overrides[get_current_customer] = lambda: admin

    try:
        response = client.patch(
            f"/api/support-tickets/{ticket_id}/status",
            json={"status": "in_progress"},
        )
    finally:
        app.dependency_overrides.pop(get_current_customer, None)

    assert response.status_code == 200
    assert response.json()["id"] == ticket_id
    assert response.json()["status"] == "in_progress"


def test_customer_cannot_update_ticket_status(client):
    """An ordinary customer cannot update a ticket's status."""

    create_test_customer(client)
    token = login_test_customer(client)

    ticket_response = client.post(
        "/api/support-tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "subject": "Delivery enquiry",
            "description": "Please provide an update on my delivery.",
        },
    )

    assert ticket_response.status_code == 201
    ticket_id = ticket_response.json()["id"]

    response = client.patch(
        f"/api/support-tickets/{ticket_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "resolved"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access required."


def test_invalid_ticket_status_is_rejected(client):
    """A status outside the allowed values must be rejected."""

    create_test_customer(client)
    token = login_test_customer(client)

    ticket_response = client.post(
        "/api/support-tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "subject": "Delivery enquiry",
            "description": "Please provide an update on my delivery.",
        },
    )

    assert ticket_response.status_code == 201
    ticket_id = ticket_response.json()["id"]

    admin = create_test_admin()
    app.dependency_overrides[get_current_customer] = lambda: admin

    try:
        response = client.patch(
            f"/api/support-tickets/{ticket_id}/status",
            json={"status": "invalid_status"},
        )
    finally:
        app.dependency_overrides.pop(get_current_customer, None)

    assert response.status_code == 422

def test_admin_cannot_update_nonexistent_ticket(client):
    """Updating a nonexistent ticket returns 404."""

    admin = create_test_admin()
    app.dependency_overrides[get_current_customer] = lambda: admin

    try:
        response = client.patch(
            "/api/support-tickets/99999/status",
            json={"status": "resolved"},
        )
    finally:
        app.dependency_overrides.pop(get_current_customer, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "Support ticket not found."


def test_unauthenticated_user_cannot_update_ticket_status(client):
    """A request without a token cannot update ticket status."""

    response = client.patch(
        "/api/support-tickets/99999/status",
        json={"status": "resolved"},
    )

    assert response.status_code == 401

def test_updated_ticket_status_persists_in_database(client):
    """The updated status remains saved after the request completes."""

    create_test_customer(client)
    customer_token = login_test_customer(client)
    customer_headers = {
        "Authorization": f"Bearer {customer_token}"
    }

    # 1. Create a ticket as an ordinary customer.
    ticket_response = client.post(
        "/api/support-tickets",
        headers=customer_headers,
        json={
            "subject": "Delivery enquiry",
            "description": "Please provide an update on my delivery.",
        },
    )

    assert ticket_response.status_code == 201
    ticket_id = ticket_response.json()["id"]

    # 2. Update the ticket as an administrator.
    admin = create_test_admin()
    app.dependency_overrides[get_current_customer] = lambda: admin

    try:
        update_response = client.patch(
            f"/api/support-tickets/{ticket_id}/status",
            json={"status": "resolved"},
        )
    finally:
        # 3. Restore normal authentication behavior.
        app.dependency_overrides.pop(get_current_customer, None)

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "resolved"

    # 4. Fetch the ticket as its owner and verify the saved status.
    fetch_response = client.get(
        "/api/support-tickets",
        headers=customer_headers,
    )

    assert fetch_response.status_code == 200

    tickets = fetch_response.json()
    updated_ticket = next(
        ticket for ticket in tickets if ticket["id"] == ticket_id
    )

    assert updated_ticket["status"] == "resolved"
