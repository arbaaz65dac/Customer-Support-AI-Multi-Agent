from app.core.security import get_current_customer
from app.database import get_db
from app.main import app
from app.models import Customer, Order, Product


def register_customer(client, email):
    response = client.post(
        "/api/customers",
        json={
            "name": "Phase Two Customer",
            "email": email,
            "password": "PhaseTwoPassword123!",
        },
    )
    assert response.status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "PhaseTwoPassword123!"},
    )
    assert login.status_code == 200
    return response.json()["id"], login.json()["access_token"]


def add_admin_identity():
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    admin = Customer(
        name="Phase Two Admin",
        email="phase-two-admin@example.com",
        password_hash="test-hash",
        role="admin",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    app.dependency_overrides[get_current_customer] = lambda: admin
    return db_generator


def test_conversation_reads_are_scoped_to_authenticated_customer(client):
    _, first_token = register_customer(client, "phase-two-a@example.com")
    _, second_token = register_customer(client, "phase-two-b@example.com")
    created = client.post(
        "/api/conversations",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"title": "Order question"},
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    own_conversation = client.get(
        f"/api/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    other_conversation = client.get(
        f"/api/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert own_conversation.status_code == 200
    assert own_conversation.json()["title"] == "Order question"
    assert other_conversation.status_code == 404

    message = client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"content": "Please check my order."},
    )
    cross_user_message = client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {second_token}"},
        json={"content": "This must not be stored."},
    )
    assert message.status_code == 201
    assert message.json()["messages"][0]["role"] == "user"
    assert cross_user_message.status_code == 404


def test_refund_request_ownership_and_admin_review(client):
    customer_id, token = register_customer(
        client, "phase-two-refund@example.com"
    )
    _, other_token = register_customer(
        client, "phase-two-refund-other@example.com"
    )
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    product = Product(
        name="Refund Test Product",
        description="A product used for refund workflow tests.",
        category="Testing",
        price="100.00",
        stock=4,
        active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    db_generator.close()

    order_response = client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "customer_id": 999999,
            "items": [{"product_id": product.id, "quantity": 1}],
        },
    )
    assert order_response.status_code == 201
    order_id = order_response.json()["id"]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    order = db.get(Order, order_id)
    assert order is not None
    order.status = "delivered"
    order.delivered_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db_generator.close()

    payload = {
        "order_id": order_id,
        "request_type": "refund",
        "reason": "The product arrived damaged and needs review.",
    }
    unauthorized = client.post(
        "/api/refund-requests",
        headers={"Authorization": f"Bearer {other_token}"},
        json=payload,
    )
    created = client.post(
        "/api/refund-requests",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert unauthorized.status_code == 404
    assert created.status_code == 201
    assert created.json()["customer_id"] == customer_id
    assert created.json()["status"] == "pending"

    customer_admin_list = client.get(
        "/api/admin/refund-requests",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert customer_admin_list.status_code == 403

    db_generator = add_admin_identity()
    try:
        orders = client.get("/api/orders/admin/all")
        assert orders.status_code == 200
        assert any(order["id"] == order_id for order in orders.json())
        updated_order = client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "delivered"},
        )
        assert updated_order.status_code == 200

        reviewed = client.patch(
            f"/api/admin/refund-requests/{created.json()['id']}",
            json={"status": "approved", "review_note": "Approved for return."},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "approved"
    finally:
        app.dependency_overrides.pop(get_current_customer, None)
        db_generator.close()


def test_admin_product_and_customer_management(client):
    customer_id, token = register_customer(
        client, "phase-two-admin-target@example.com"
    )
    db_generator = add_admin_identity()
    try:
        created_product = client.post(
            "/api/products",
            json={
                "name": "Managed Product",
                "description": "Product management test.",
                "category": "Testing",
                "price": "250.00",
                "stock": 5,
                "active": True,
            },
        )
        assert created_product.status_code == 201
        product_id = created_product.json()["id"]
        updated = client.patch(
            f"/api/products/{product_id}",
            json={
                "name": "Updated Managed Product",
                "description": "Updated description.",
                "category": "Testing",
                "price": "275.00",
                "stock": 8,
                "active": True,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Updated Managed Product"

        customer_list = client.get("/api/customers/admin/all")
        assert customer_list.status_code == 200
        assert customer_id in {entry["id"] for entry in customer_list.json()}
        customer_detail = client.get(f"/api/customers/admin/{customer_id}")
        assert customer_detail.status_code == 200
        assert customer_detail.json()["email"] == "phase-two-admin-target@example.com"
        deactivated = client.patch(
            f"/api/customers/admin/{customer_id}/active",
            json={"active": False},
        )
        assert deactivated.status_code == 200
        assert deactivated.json()["active"] is False

        deleted = client.delete(f"/api/products/{product_id}")
        assert deleted.status_code == 204
        assert client.get(f"/api/products/{product_id}").status_code == 404

        app.dependency_overrides.pop(get_current_customer, None)
        db_generator.close()
        db_generator = None
        assert client.get(
            f"/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_customer, None)
        if db_generator is not None:
            db_generator.close()
from datetime import datetime, timezone
