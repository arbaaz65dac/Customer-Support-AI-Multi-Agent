
def test_create_and_list_products(client):
    # Create a product through the public API.
    response = client.post(
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

    # Retrieve products through the API.
    response = client.get("/api/products")

    assert response.status_code == 200
    products = response.json()
    assert len(products) == 1
    assert products[0]["id"] == created_product["id"]


def test_search_products_by_query(client):
    # Seed two products using the API.
    client.post(
        "/api/products",
        json={
            "name": "Wireless Mouse",
            "description": "Computer accessory",
            "category": "Electronics",
            "price": "799.00",
            "stock": 10,
            "active": True,
        },
    )

    client.post(
        "/api/products",
        json={
            "name": "Office Chair",
            "description": "Comfortable desk chair",
            "category": "Furniture",
            "price": "4999.00",
            "stock": 5,
            "active": True,
        },
    )

    response = client.get(
        "/api/products",
        params={"query": "mouse"},
    )

    assert response.status_code == 200
    products = response.json()
    assert len(products) == 1
    assert products[0]["name"] == "Wireless Mouse"


def test_negative_price_is_rejected(client):
    response = client.post(
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
