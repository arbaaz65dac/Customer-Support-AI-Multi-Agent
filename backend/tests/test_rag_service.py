
from app.services import rag_service


def test_rag_returns_fallback_without_calling_llm(monkeypatch):
    """No accepted evidence must result in a fallback, not an LLM guess."""

    # Simulate retrieval finding no sufficiently relevant evidence.
    monkeypatch.setattr(
        rag_service,
        "retrieve_relevant_knowledge",
        lambda question: [],
    )

    # If the LLM is invoked, fail the test immediately.
    def unexpected_llm_call(*args, **kwargs):
        raise AssertionError(
            "The LLM must not be called when retrieval returns no evidence"
        )

    monkeypatch.setattr(
        rag_service,
        "ChatGroq",
        unexpected_llm_call,
    )

    result = rag_service.answer_from_knowledge(
        "Does the company have a support office on Mars?"
    )

    assert "couldn't find sufficiently relevant information" in (
        result["answer"].lower()
    )
    assert result["sources"] == []
    assert result["retrieved_chunks"] == 0
    assert result["retrieval_distances"] == []


def test_rag_rejects_empty_question():
    import pytest

    with pytest.raises(ValueError, match="Question cannot be empty"):
        rag_service.answer_from_knowledge("   ")
