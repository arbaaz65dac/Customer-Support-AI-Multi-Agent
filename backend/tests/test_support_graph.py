
from app.agents.support_graph import support_graph


def test_policy_question_routes_to_knowledge_agent(monkeypatch):
    """Verify routing and mapping of the existing RAG service response."""

    def fake_answer_from_knowledge(question):
        assert question == "What is the refund policy?"

        return {
            "answer": "The policy does not specify a refund timeline.",
            "sources": ["returns_refunds_policy.md"],
            "retrieved_chunks": 2,
            "retrieval_distances": [0.42, 0.61],
        }

    monkeypatch.setattr(
        "app.services.rag_service.answer_from_knowledge",
        fake_answer_from_knowledge,
    )

    result = support_graph.invoke(
        {"question": "What is the refund policy?"}
    )

    assert result["intent"] == "policy_question"
    assert result["selected_agent"] == "knowledge"
    assert result["answer"] == (
        "The policy does not specify a refund timeline."
    )
    assert result["sources"] == ["returns_refunds_policy.md"]
    assert result["retrieved_chunks"] == 2


def test_product_question_routes_to_product_order_agent():
    """Verify the product agent requires a database session."""

    result = support_graph.invoke(
        {"question": "Find products under 2000"}
    )

    assert result["intent"] == "product_search"
    assert result["selected_agent"] == "product_order"
    assert "database session is required" in result["answer"].lower()



def test_product_agent_uses_existing_tool_service(monkeypatch):
    """Verify the graph forwards the DB and trusted customer ID."""

    fake_db = object()
    trusted_customer_id = 123
    expected_question = "Find products under 2000"

    def fake_answer_with_tools(
        message,
        db,
        trusted_customer_id=None,
    ):
        assert message == expected_question
        assert db is fake_db
        assert trusted_customer_id == 123

        return "I found two matching products."

    monkeypatch.setattr(
        "app.agents.support_graph.answer_with_tools",
        fake_answer_with_tools,
    )

    result = support_graph.invoke(
        {"question": expected_question},
        context={
            "db": fake_db,
            "customer_id": trusted_customer_id,
        },
    )

    assert result["intent"] == "product_search"
    assert result["selected_agent"] == "product_order"
    assert result["answer"] == "I found two matching products."


def test_order_question_routes_to_product_order_agent():
    """Verify order questions select the Product & Order Agent."""

    result = support_graph.invoke(
        {"question": "Where is my order?"}
    )

    assert result["intent"] == "order_status"
    assert result["selected_agent"] == "product_order"
    assert "database session is required" in result["answer"].lower()


def test_general_question_routes_to_general_agent():
    """Verify general questions select the general agent."""

    result = support_graph.invoke(
        {"question": "Hello there!"}
    )

    assert result["intent"] == "general_question"
    assert result["selected_agent"] == "general"
    assert "General support agent selected" in result["answer"]


def test_graph_preserves_original_question():
    """Verify graph execution preserves the customer's original question."""

    question = "What is the delivery policy?"

    result = support_graph.invoke({"question": question})

    assert result["question"] == question
