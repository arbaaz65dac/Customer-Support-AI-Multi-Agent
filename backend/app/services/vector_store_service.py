
import hashlib
from pathlib import Path
import math

from langchain_chroma import Chroma
from app.services.document_service import load_and_split_documents
from app.core.config import RAG_TOP_K, RAG_MAX_DISTANCE
from app.services.provider_service import create_gemini_embeddings


# Store the local vector database inside backend/data/chroma.
BACKEND_DIR = Path(__file__).resolve().parents[2]
CHROMA_DIR = BACKEND_DIR / "data" / "chroma"

COLLECTION_NAME = "customer_support_knowledge_v1"


def create_embeddings():
    """Create the Gemini embedding model."""
    return create_gemini_embeddings()


def create_vector_store():
    """
    Open or create the persistent Chroma collection.

    The embedding function is attached to the collection so
    later searches can embed questions using the same model.
    """

    embeddings = create_embeddings()

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )


def _make_chunk_id(source: str, start_index: int, content: str) -> str:
    """
    Generate a repeatable ID for a chunk.

    Stable IDs help avoid duplicate records when the same
    documents are indexed again.
    """

    unique_value = f"{source}|{start_index}|{content}"
    return hashlib.sha256(unique_value.encode("utf-8")).hexdigest()


def index_knowledge_documents() -> int:
    """
    Load, split, embed, and store the support documents.

    Returns the number of chunks submitted to Chroma.
    """

    chunks = load_and_split_documents()

    if not chunks:
        raise ValueError("No document chunks available for indexing")

    vector_store = create_vector_store()

    policies = list(
        {
            chunk.metadata.get("policy", "unknown")
            for chunk in chunks
        }
    )
    existing = vector_store.get(
        where={"policy": {"$in": policies}},
        include=[],
    )
    existing_ids = set(existing.get("ids", []))

    # Keep IDs stable across repeated indexing of unchanged chunks.
    ids = [
        _make_chunk_id(
            source=(
                f"{chunk.metadata.get('source', 'unknown')}|"
                f"{chunk.metadata.get('version', 'unknown')}|"
                f"{chunk.metadata.get('effective_date', 'unknown')}"
            ),
            start_index=chunk.metadata.get("start_index", 0),
            content=chunk.page_content,
        )
        for chunk in chunks
    ]

    # Chroma computes embeddings and stores text, vectors and metadata.
    # Reusing IDs makes indexing unchanged chunks repeatable.
    vector_store.add_documents(
        documents=chunks,
        ids=ids,
    )
    stale_ids = existing_ids.difference(ids)
    if stale_ids:
        vector_store.delete(ids=sorted(stale_ids))

    return len(chunks)


def search_knowledge(query: str, k: int = 3):
    """Search indexed policy chunks for a development or support query."""

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    if not 1 <= k <= 10:
        raise ValueError("k must be between 1 and 10")

    vector_store = create_vector_store()

    return vector_store.similarity_search(
        query=query.strip(),
        k=k,
    )


def retrieve_relevant_knowledge(
    query: str,
    k: int | None = None,
) -> list[dict]:
    """
    Retrieve chunks and filter out candidates whose Chroma distance
    exceeds the configured maximum.

    Lower Chroma distances indicate closer matches for the collection's
    configured distance metric. The threshold must be calibrated.
    """

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    result_count = RAG_TOP_K if k is None else k

    if not 1 <= result_count <= 10:
        raise ValueError("k must be between 1 and 10")

    vector_store = create_vector_store()

    candidates = vector_store.similarity_search_with_score(
        query=query.strip(),
        k=result_count,
    )

    relevant_results = []

    for document, distance in candidates:
        distance = float(distance)

        # Skip malformed scores rather than treating them as evidence.
        if not math.isfinite(distance):
            continue

        # Discard candidates beyond the calibrated distance threshold.
        if distance > RAG_MAX_DISTANCE:
            continue

        relevant_results.append(
            {
                "document": document,
                "distance": distance,
            }
        )

    return relevant_results
