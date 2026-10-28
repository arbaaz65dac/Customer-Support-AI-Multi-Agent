from app.api.chat_routes import generate_answer


def test_chat_returns_generated_answer(client, monkeypatch):
    # Replace the real LLM call with a predictable response.
    monkeypatch.setattr(
        "app.api.chat_routes.generate_answer",
        lambda message: f"Test answer for: {message}",
    )

    response = client.post(
        "/api/chat/ask",
        json={"message": "Where can I find delivery information?"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == (
        "Test answer for: Where can I find delivery information?"
    )


def test_chat_rejects_empty_message(client):
    response = client.post(
        "/api/chat/ask",
        json={"message": "   "},
    )

    assert response.status_code == 422


def test_chat_rejects_message_over_limit(client):
    response = client.post(
        "/api/chat/ask",
        json={"message": "a" * 2001},
    )

    assert response.status_code == 422


def test_chat_handles_provider_failure(client, monkeypatch):
    def fail_to_generate(message):
        raise Exception("Simulated provider failure")

    monkeypatch.setattr(
        "app.api.chat_routes.generate_answer",
        fail_to_generate,
    )

    response = client.post(
        "/api/chat/ask",
        json={"message": "Hello"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "The AI service could not generate a response."
    )