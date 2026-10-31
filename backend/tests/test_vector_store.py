
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_chroma import Chroma


class FakeEmbeddings(Embeddings):
    """
    Tiny deterministic embeddings for tests only.
    These are not suitable for real semantic search.
    """

    def _embed(self, text: str) -> list[float]:
        # Make a simple vector from a few characters.
        # This is only to exercise the vector-store interface.
        return [
            float(sum(ord(char) for char in text) % 101),
            float(len(text) % 101),
            float(text.lower().count("delivery")),
        ]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def test_chroma_stores_documents_and_metadata(tmp_path):
    store = Chroma(
        collection_name="test_support_docs",
        embedding_function=FakeEmbeddings(),
        persist_directory=str(tmp_path / "chroma"),
    )

    store.add_documents(
        documents=[
            Document(
                page_content="Delayed deliveries should be investigated by support.",
                metadata={"source": "delivery_policy.md"},
            )
        ],
        ids=["delivery-test-1"],
    )

    results = store.similarity_search("delivery", k=1)

    assert len(results) == 1
    assert results[0].metadata["source"] == "delivery_policy.md"
    assert "support" in results[0].page_content


def test_chroma_persists_documents_between_instances(tmp_path):
    directory = str(tmp_path / "persistent_chroma")
    embeddings = FakeEmbeddings()

    first_store = Chroma(
        collection_name="persistence_test",
        embedding_function=embeddings,
        persist_directory=directory,
    )

    first_store.add_documents(
        documents=[
            Document(
                page_content="Refund timing depends on the payment method.",
                metadata={"source": "returns_refunds_policy.md"},
            )
        ],
        ids=["refund-test-1"],
    )

    # Open a second instance pointing to the same persistent directory.
    second_store = Chroma(
        collection_name="persistence_test",
        embedding_function=embeddings,
        persist_directory=directory,
    )

    results = second_store.similarity_search("refund", k=1)

    assert len(results) == 1
    assert results[0].metadata["source"] == "returns_refunds_policy.md"


def test_chroma_returns_empty_list_for_empty_collection(tmp_path):
    store = Chroma(
        collection_name="empty_test",
        embedding_function=FakeEmbeddings(),
        persist_directory=str(tmp_path / "empty_chroma"),
    )

    results = store.similarity_search("unknown question", k=3)

    assert results == []


def test_index_replaces_stale_chunks_after_successful_upsert(monkeypatch):
    from app.services import vector_store_service

    documents = [
        Document(
            page_content="Return requests can be made within seven days.",
            metadata={
                "source": "returns_policy_v1.md",
                "policy": "returns_policy",
                "version": "1.0",
                "effective_date": "2026-10-31",
                "start_index": 0,
            },
        )
    ]

    class FakeVectorStore:
        def __init__(self):
            self.deleted_ids = []
            self.added_ids = []

        def get(self, where, include):
            assert where == {"policy": {"$in": ["returns_policy"]}}
            assert include == []
            return {"ids": ["stale-policy-chunk"]}

        def add_documents(self, documents, ids):
            self.added_ids = ids
            assert len(documents) == 1

        def delete(self, ids):
            self.deleted_ids = ids

    store = FakeVectorStore()
    monkeypatch.setattr(
        vector_store_service,
        "load_and_split_documents",
        lambda: documents,
    )
    monkeypatch.setattr(
        vector_store_service,
        "create_vector_store",
        lambda: store,
    )

    indexed_count = vector_store_service.index_knowledge_documents()

    assert indexed_count == 1
    assert len(store.added_ids) == 1
    assert store.deleted_ids == ["stale-policy-chunk"]
