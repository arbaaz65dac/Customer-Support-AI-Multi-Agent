
from langchain_core.documents import Document

from app.services import vector_store_service


def test_retrieval_keeps_candidates_within_threshold(monkeypatch):
    relevant_doc = Document(
        page_content="Delayed deliveries should be investigated.",
        metadata={"source": "delivery_policy.md"},
    )
    weak_doc = Document(
        page_content="Unrelated catalogue information.",
        metadata={"source": "faq.md"},
    )

    # Simulate Chroma results with one close match and one distant match.
    class FakeVectorStore:
        def similarity_search_with_score(self, query, k):
            return [
                (relevant_doc, 0.4),
                (weak_doc, 2.4),
            ]

    monkeypatch.setattr(
        vector_store_service,
        "create_vector_store",
        lambda: FakeVectorStore(),
    )
    monkeypatch.setattr(
        vector_store_service,
        "RAG_MAX_DISTANCE",
        1.5,
    )

    results = vector_store_service.retrieve_relevant_knowledge(
        "What happens when delivery is delayed?",
        k=3,
    )

    assert len(results) == 1
    assert results[0]["document"].metadata["source"] == (
        "delivery_policy.md"
    )
    assert results[0]["distance"] == 0.4


def test_retrieval_returns_empty_when_all_candidates_are_weak(
    monkeypatch,
):
    weak_doc = Document(
        page_content="Unrelated content.",
        metadata={"source": "faq.md"},
    )

    class FakeVectorStore:
        def similarity_search_with_score(self, query, k):
            return [(weak_doc, 3.0)]

    monkeypatch.setattr(
        vector_store_service,
        "create_vector_store",
        lambda: FakeVectorStore(),
    )
    monkeypatch.setattr(
        vector_store_service,
        "RAG_MAX_DISTANCE",
        1.5,
    )

    results = vector_store_service.retrieve_relevant_knowledge(
        "Does the company deliver to Antarctica?",
        k=3,
    )

    assert results == []


def test_retrieval_rejects_empty_query():
    import pytest

    with pytest.raises(ValueError, match="cannot be empty"):
        vector_store_service.retrieve_relevant_knowledge("   ")


def test_retrieval_rejects_invalid_k():
    import pytest

    with pytest.raises(ValueError, match="between 1 and 10"):
        vector_store_service.retrieve_relevant_knowledge(
            "delivery",
            k=0,
        )
