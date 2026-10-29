
def test_support_graph_endpoint_returns_graph_result(client, monkeypatch):
    """Test the endpoint without calling the real LLM or database tools."""

    def fake_invoke(state, context):
        assert state["question"] == "What is the refund policy?"
        assert "db" in context

        return {
            "question": state["question"],
            "intent": "policy_question",
            "selected_agent": "knowledge",
            "answer": "The policy does not specify a refund timeline.",
            "sources": ["returns_refunds_policy.md"],
            "retrieved_chunks": 2,
        }

    monkeypatch.setattr(
        "app.api.support_graph_routes.support_graph.invoke",
        fake_invoke,
    )

    response = client.post(
        "/api/support/ask",
        json={"question": "What is the refund policy?"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["intent"] == "policy_question"
    assert data["selected_agent"] == "knowledge"
    assert "does not specify" in data["answer"]
    assert data["sources"] == ["returns_refunds_policy.md"]
    assert data["retrieved_chunks"] == 2


def test_support_graph_endpoint_rejects_missing_question(client):
    response = client.post("/api/support/ask", json={})

    assert response.status_code == 422


def test_support_graph_endpoint_rejects_blank_question(client):
    response = client.post(
        "/api/support/ask",
        json={"question": "   "},
    )

    assert response.status_code == 422


def test_support_graph_endpoint_handles_runtime_failure(client, monkeypatch):
    def fail_invoke(state, context):
        raise RuntimeError("Simulated provider failure")

    monkeypatch.setattr(
        "app.api.support_graph_routes.support_graph.invoke",
        fail_invoke,
    )

    response = client.post(
        "/api/support/ask",
        json={"question": "What is the refund policy?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The support assistant is currently unavailable."
    )
