def test_agent_endpoint_returns_answer(client, monkeypatch):
    # Mock the agent so this test never calls Groq.
    def fake_answer(message, db):
        return "I found two products matching your search."

    monkeypatch.setattr(
        "app.api.chat_routes.answer_with_tools",
        fake_answer,
    )

    response = client.post(
        "/api/chat/agent",
        json={"message": "Find me a product"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == (
        "I found two products matching your search."
    )


def test_agent_endpoint_rejects_empty_message(client):
    response = client.post(
        "/api/chat/agent",
        json={"message": "   "},
    )

    assert response.status_code == 422


def test_agent_endpoint_handles_runtime_error(client, monkeypatch):
    def fail_to_answer(message, db):
        raise RuntimeError("Simulated agent failure")

    monkeypatch.setattr(
        "app.api.chat_routes.answer_with_tools",
        fail_to_answer,
    )

    response = client.post(
        "/api/chat/agent",
        json={"message": "Find me a product"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The AI service is currently unavailable."
    )