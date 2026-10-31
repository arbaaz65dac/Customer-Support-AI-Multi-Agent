import pytest

from app.services import provider_service


def test_groq_factory_uses_configured_model_and_timeout(monkeypatch):
    observed = {}

    def fake_chat_groq(**kwargs):
        observed.update(kwargs)
        return "configured-chat-client"

    monkeypatch.setattr(provider_service, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(provider_service, "GROQ_MODEL", "test-model")
    monkeypatch.setattr(provider_service, "ChatGroq", fake_chat_groq)

    client = provider_service.create_groq_chat_model(
        temperature=0.25,
        timeout=12,
    )

    assert client == "configured-chat-client"
    assert observed == {
        "model": "test-model",
        "temperature": 0.25,
        "max_tokens": 500,
        "api_key": "test-key",
        "timeout": 12,
        "max_retries": 1,
    }


def test_provider_factories_report_missing_secrets(monkeypatch):
    monkeypatch.setattr(provider_service, "GROQ_API_KEY", "")
    monkeypatch.setattr(provider_service, "GOOGLE_API_KEY", "")

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        provider_service.create_groq_chat_model()
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        provider_service.create_gemini_embeddings()
