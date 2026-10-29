
from app.core.security import get_current_customer
from app.database import get_db
from app.main import app
from app.models import Customer


def create_test_customer(client):
    """Register a customer and return their ID."""
    response = client.post(
        "/api/customers",
        json={
            "name": "Order Test Customer",
            "email": "order-test@example.com",
            "password": "DemoPassword123!",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def login_test_customer(client):
    """Log in and return the bearer token."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "order-test@example.com",
            "password": "DemoPassword123!",
        },
    )

    assert response.status_code == 200
    return response.json()["access_token"]


def create_test_product(client, stock=5):
    """Create a test product using a temporary administrator identity."""

    # Obtain the same test database session used by the API.
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    admin = Customer(
        name="Order Test Admin",
        email="order-admin-test@example.com",
        password_hash="test-password-hash",
        role="admin",
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Temporarily authenticate this request as the administrator.
    app.dependency_overrides[get_current_customer] = lambda: admin

    try:
        response = client.post(
            "/api/products",
            json={
                "name": "Order Test Product",
                "description": "Product for order tests",
                "category": "Testing",
                "price": "100.00",
                "stock": stock,
                "active": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_customer, None)
        db_generator.close()

    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_create_order_reduces_stock(client):
    customer_id = create_test_customer(client)
    product_id = create_test_product(client, stock=5)
    token = login_test_customer(client)

    response = client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": 2}],
        },
    )

    assert response.status_code == 201, response.text

    order = response.json()
    assert order["status"] == "pending"
    assert order["items"][0]["quantity"] == 2

    product_response = client.get(f"/api/products/{product_id}")
    assert product_response.status_code == 200
    assert product_response.json()["stock"] == 3


def test_insufficient_stock_does_not_create_order(client):
    customer_id = create_test_customer(client)
    product_id = create_test_product(client, stock=1)
    token = login_test_customer(client)

    response = client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": 2}],
        },
    )

    assert response.status_code == 409

    product_response = client.get(f"/api/products/{product_id}")
    assert product_response.status_code == 200
    assert product_response.json()["stock"] == 1


def test_order_uses_authenticated_customer_not_body_customer_id(client):
    """A request cannot create an order for a different customer."""

    authenticated_customer_id = create_test_customer(client)
    product_id = create_test_product(client, stock=5)
    token = login_test_customer(client)

    response = client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "customer_id": 99999,
            "items": [{"product_id": product_id, "quantity": 1}],
        },
    )

    assert response.status_code == 201, response.text

    order = response.json()
    order_id = order["id"]
    assert order["customer_id"] == authenticated_customer_id

    order_response = client.get(
        f"/api/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert order_response.status_code == 200
    assert order_response.json()["id"] == order_id
    assert order_response.json()["customer_id"] == authenticated_customer_id
