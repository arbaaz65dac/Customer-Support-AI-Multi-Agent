from types import SimpleNamespace

from app.core.security import get_current_customer
from app.database import get_db
from app.models import Customer, Order


def test_chat_cannot_reveal_another_customers_order(
    client,
    monkeypatch,
):
    db_generator = client.app.dependency_overrides[get_db]()
    db = next(db_generator)
    owner = Customer(
        name="Authenticated Order Owner",
        email="chat-owner@example.test",
        password_hash="test-hash",
    )
    other_customer = Customer(
        name="Private Customer",
        email="chat-other@example.test",
        password_hash="test-hash",
    )
    db.add_all([owner, other_customer])
    db.flush()
    foreign_order = Order(customer_id=other_customer.id, status="shipped")
    db.add(foreign_order)
    db.commit()
    foreign_order_id = foreign_order.id
    owner_id = owner.id
    db_generator.close()

    client.app.dependency_overrides[get_current_customer] = (
        lambda: SimpleNamespace(id=owner_id, role="customer")
    )

    class FakeLLM:
        def __init__(self):
            self.call_count = 0

        def bind_tools(self, tools):
            self.tools = {item.name: item for item in tools}
            return self

        def invoke(self, messages):
            self.call_count += 1
            if self.call_count == 1:
                return SimpleNamespace(
                    tool_calls=[
                        {
                            "name": "get_order_status",
                            "args": {"order_id": foreign_order_id},
                        }
                    ],
                    content="",
                )

            support_results = messages[-1].content
            assert "Order not found" in support_results
            assert '"status": "shipped"' not in support_results
            assert "Private Customer" not in support_results
            return SimpleNamespace(
                content="I could not find that order in your account."
            )

    fake_llm = FakeLLM()
    monkeypatch.setattr(
        "app.services.tool_agent_service.GROQ_API_KEY",
        "test-key",
    )
    monkeypatch.setattr(
        "app.services.tool_agent_service.create_groq_chat_model",
        lambda **kwargs: fake_llm,
    )

    response = client.post(
        "/api/support/ask",
        json={
            "question": (
                f"Check my order {foreign_order_id} and tell me its status."
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["intent"] == "order_status"
    assert "could not find that order" in response.json()["answer"].lower()
    assert "shipped" not in response.json()["answer"].lower()
