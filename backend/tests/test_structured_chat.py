from app.schemas.chat import ChatAssistantResponse


def test_structured_chat_returns_validated_fields(client, monkeypatch):
    # Simulate a valid structured response without calling Groq.
    expected = ChatAssistantResponse(
        intent="create_ticket",
        answer="You can provide your issue details to start a support request.",
        suggested_action="create_support_ticket",
    )

    monkeypatch.setattr(
        "app.api.chat_routes.generate_structured_answer",
        lambda message: expected,
    )

    response = client.post(
        "/api/chat/structured",
        json={"message": "I want to raise a support ticket"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["intent"] == "create_ticket"
    assert data["suggested_action"] == "create_support_ticket"
    assert data["answer"]


def test_structured_chat_rejects_empty_message(client):
    response = client.post(
        "/api/chat/structured",
        json={"message": "   "},
    )

    assert response.status_code == 422


def test_structured_chat_handles_provider_failure(client, monkeypatch):
    def fail_to_generate(message):
        raise Exception("Simulated provider failure")

    monkeypatch.setattr(
        "app.api.chat_routes.generate_structured_answer",
        fail_to_generate,
    )

    response = client.post(
        "/api/chat/structured",
        json={"message": "Hello"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "The AI service could not generate a response."
    )