
def test_rag_endpoint_returns_answer_and_sources(client, monkeypatch):
    # Avoid calling Chroma, Gemini, or Groq in this unit test.
    def fake_answer(question):
        return {
            "answer": (
                "If a delivery is delayed, contact support with your "
                "order reference."
            ),
            "sources": ["shipping_policy_v1.md"],
            "citations": [
                {
                    "source": "shipping_policy_v1.md",
                    "policy": "shipping_policy",
                    "version": "1.0",
                    "effective_date": "2026-10-31",
                    "excerpt": "Contact support with your order ID.",
                }
            ],
            "retrieved_chunks": 2,
        }

    monkeypatch.setattr(
        "app.api.rag_routes.answer_from_knowledge",
        fake_answer,
    )

    response = client.post(
        "/api/rag/ask",
        json={
            "question": "What should I do about a delayed delivery?"
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert "contact support" in data["answer"].lower()
    assert data["sources"] == ["shipping_policy_v1.md"]
    assert data["citations"][0]["version"] == "1.0"
    assert data["citations"][0]["source"] == "shipping_policy_v1.md"
    assert data["retrieved_chunks"] == 2


def test_rag_endpoint_rejects_missing_question(client):
    response = client.post(
        "/api/rag/ask",
        json={},
    )

    assert response.status_code == 422


def test_rag_endpoint_handles_service_failure(client, monkeypatch):
    def fail_to_answer(question):
        raise RuntimeError("Simulated RAG service failure")

    monkeypatch.setattr(
        "app.api.rag_routes.answer_from_knowledge",
        fail_to_answer,
    )

    response = client.post(
        "/api/rag/ask",
        json={"question": "What is the refund policy?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The RAG service is currently unavailable."
    )
