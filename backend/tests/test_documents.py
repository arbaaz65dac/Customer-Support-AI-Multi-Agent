
from app.services.document_service import (
    load_documents,
    split_documents,
)


def test_load_documents_returns_all_knowledge_files():
    documents = load_documents()

    assert len(documents) == 5
    assert {
        document.metadata["source"] for document in documents
    } == {
        "returns_policy_v1.md",
        "refunds_policy_v1.md",
        "shipping_policy_v1.md",
        "warranty_policy_v1.md",
        "faq_v1.md",
    }

    for document in documents:
        assert document.page_content.strip()
        assert document.metadata.get("source", "").endswith(".md")
        assert document.metadata.get("version") == "1.0"
        assert document.metadata.get("effective_date") == "2026-10-31"
        assert document.metadata.get("policy")


def test_loaded_documents_contain_expected_content():
    documents = load_documents()

    combined_text = "\n".join(
        document.page_content for document in documents
    )

    assert "Customer Support FAQ" in combined_text
    assert "Shipping and Delivery Policy" in combined_text
    assert "Returns Policy" in combined_text
    assert "Refunds Policy" in combined_text
    assert "Warranty Policy" in combined_text
    assert "₹" in combined_text


def test_split_documents_preserves_source_metadata():
    documents = load_documents()
    chunks = split_documents(documents)

    assert len(chunks) >= len(documents)

    # Every chunk should retain the source and version evidence.
    for chunk in chunks:
        assert chunk.page_content.strip()
        assert chunk.metadata.get("source", "").endswith(".md")
        assert chunk.metadata.get("version") == "1.0"
        assert chunk.metadata.get("effective_date") == "2026-10-31"


def test_split_documents_adds_start_index():
    documents = load_documents()
    chunks = split_documents(documents)

    # start_index helps locate the chunk in its original document.
    for chunk in chunks:
        assert isinstance(chunk.metadata.get("start_index"), int)
        assert chunk.metadata["start_index"] >= 0


def test_document_loader_rejects_unversioned_policy(tmp_path, monkeypatch):
    import pytest

    from app.services import document_service

    monkeypatch.setattr(document_service, "KNOWLEDGE_BASE_DIR", tmp_path)
    (tmp_path / "policy.md").write_text(
        "This policy has no version.",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="No Markdown documents"):
        document_service.load_documents()


def test_document_loader_selects_latest_version_per_policy(tmp_path, monkeypatch):
    from app.services import document_service

    monkeypatch.setattr(document_service, "KNOWLEDGE_BASE_DIR", tmp_path)
    (tmp_path / "returns_policy_v1.md").write_text(
        "Returns v1\n\nPolicy version: 1.0\nEffective date: 2026-01-01\n",
        encoding="utf-8",
    )
    (tmp_path / "returns_policy_v2.md").write_text(
        "Returns v2\n\nPolicy version: 2.0\nEffective date: 2026-10-31\n",
        encoding="utf-8",
    )

    documents = document_service.load_documents()

    assert len(documents) == 1
    assert documents[0].metadata["source"] == "returns_policy_v2.md"
    assert documents[0].metadata["version"] == "2.0"
