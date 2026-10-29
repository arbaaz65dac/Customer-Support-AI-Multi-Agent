
import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_customer
from app.database import get_db
from app.main import app
from app.models import Customer


@pytest.fixture
def product_test_client(client):
    """Provide a client with a test administrator in the test database."""

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    admin = Customer(
        name="Test Admin",
        email="admin-test@example.com",
        password_hash="test-password-hash",
        role="admin",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    app.dependency_overrides[get_current_customer] = lambda: admin

    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_customer, None)
        db_generator.close()


def test_create_and_list_products(product_test_client):
    response = product_test_client.post(
        "/api/products",
        json={
            "name": "Wireless Mouse",
            "description": "Wireless mouse for everyday computing",
            "category": "Electronics",
            "price": "799.00",
            "stock": 10,
            "active": True,
        },
    )

    assert response.status_code == 201
    created_product = response.json()
    assert created_product["name"] == "Wireless Mouse"

    # Product browsing remains public.
    response = product_test_client.get("/api/products")

    assert response.status_code == 200
    products = response.json()
    assert len(products) == 1
    assert products[0]["id"] == created_product["id"]


def test_search_products_by_query(product_test_client):
    for name, description, category, price, stock in [
        (
            "Wireless Mouse",
            "Computer accessory",
            "Electronics",
            "799.00",
            10,
        ),
        (
            "Office Chair",
            "Comfortable desk chair",
            "Furniture",
            "4999.00",
            5,
        ),
    ]:
        response = product_test_client.post(
            "/api/products",
            json={
                "name": name,
                "description": description,
                "category": category,
                "price": price,
                "stock": stock,
                "active": True,
            },
        )
        assert response.status_code == 201

    response = product_test_client.get(
        "/api/products",
        params={"query": "mouse"},
    )

    assert response.status_code == 200
    products = response.json()
    assert len(products) == 1
    assert products[0]["name"] == "Wireless Mouse"


def test_negative_price_is_rejected(product_test_client):
    response = product_test_client.post(
        "/api/products",
        json={
            "name": "Invalid Product",
            "description": "Invalid price test",
            "category": "Testing",
            "price": "-10.00",
            "stock": 1,
            "active": True,
        },
    )

    assert response.status_code == 422


def test_missing_product_returns_404(client):
    response = client.get("/api/products/99999")

    assert response.status_code == 404


def test_customer_cannot_create_product(client):
    """An authenticated ordinary customer must not create products."""

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)

    customer = Customer(
        name="Ordinary Customer",
        email="ordinary-product-test@example.com",
        password_hash="test-password-hash",
        role="customer",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    app.dependency_overrides[get_current_customer] = lambda: customer

    try:
        response = client.post(
            "/api/products",
            json={
                "name": "Unauthorized Product",
                "description": "This should not be created",
                "category": "Testing",
                "price": "100.00",
                "stock": 1,
                "active": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_customer, None)
        db_generator.close()

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access required."


def test_product_creation_requires_authentication(client):
    """Reject product creation without authentication."""

    response = client.post(
        "/api/products",
        json={
            "name": "Unauthorized Product",
            "description": "This should not be created",
            "category": "Testing",
            "price": "100.00",
            "stock": 1,
            "active": True,
        },
    )

    assert response.status_code == 401
