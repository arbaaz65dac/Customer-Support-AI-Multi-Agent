
from app.models import Customer, Product


def create_test_customer(client):
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


def create_test_product(client, stock=5):
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
    assert response.status_code == 201
    return response.json()["id"]


def test_create_order_reduces_stock(client):
    customer_id = create_test_customer(client)
    product_id = create_test_product(client, stock=5)

    response = client.post(
        "/api/orders",
        json={
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": 2}],
        },
    )

    assert response.status_code == 201
    order = response.json()
    assert order["status"] == "pending"
    assert order["items"][0]["quantity"] == 2

    # Verify remaining stock through the product API.
    product_response = client.get(f"/api/products/{product_id}")
    assert product_response.status_code == 200
    assert product_response.json()["stock"] == 3


def test_insufficient_stock_does_not_create_order(client):
    customer_id = create_test_customer(client)
    product_id = create_test_product(client, stock=1)

    response = client.post(
        "/api/orders",
        json={
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": 2}],
        },
    )

    assert response.status_code == 409

    product_response = client.get(f"/api/products/{product_id}")
    assert product_response.status_code == 200
    assert product_response.json()["stock"] == 1


def test_order_for_missing_customer_fails(client):
    product_id = create_test_product(client, stock=5)

    response = client.post(
        "/api/orders",
        json={
            "customer_id": 99999,
            "items": [{"product_id": product_id, "quantity": 1}],
        },
    )

    assert response.status_code == 404
