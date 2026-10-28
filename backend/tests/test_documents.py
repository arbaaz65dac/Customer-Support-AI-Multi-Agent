
from app.services.document_service import (
    load_documents,
    split_documents,
)


def test_load_documents_returns_all_knowledge_files():
    documents = load_documents()

    # We created three Markdown files for this exercise.
    assert len(documents) == 3

    # Each document should have text and source metadata.
    for document in documents:
        assert document.page_content.strip()
        assert document.metadata.get("source", "").endswith(".md")


def test_loaded_documents_contain_expected_content():
    documents = load_documents()

    combined_text = "\n".join(
        document.page_content for document in documents
    )

    assert "Customer Support FAQ" in combined_text
    assert "Delivery Policy" in combined_text
    assert "Returns and Refunds Policy" in combined_text


def test_split_documents_preserves_source_metadata():
    documents = load_documents()
    chunks = split_documents(documents)

    assert len(chunks) >= len(documents)

    # Every chunk should retain its source filename.
    for chunk in chunks:
        assert chunk.page_content.strip()
        assert chunk.metadata.get("source", "").endswith(".md")


def test_split_documents_adds_start_index():
    documents = load_documents()
    chunks = split_documents(documents)

    # start_index helps locate the chunk in its original document.
    for chunk in chunks:
        assert isinstance(chunk.metadata.get("start_index"), int)
        assert chunk.metadata["start_index"] >= 0
