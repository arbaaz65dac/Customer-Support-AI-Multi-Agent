
import hashlib
from pathlib import Path

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import GOOGLE_API_KEY, GEMINI_EMBEDDING_MODEL
from app.services.document_service import load_and_split_documents


# Store the local vector database inside backend/data/chroma.
BACKEND_DIR = Path(__file__).resolve().parents[2]
CHROMA_DIR = BACKEND_DIR / "data" / "chroma"

COLLECTION_NAME = "customer_support_knowledge"


def create_embeddings():
    """Create the Gemini embedding model."""

    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not configured")

    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )


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

    # Keep IDs stable across repeated indexing of unchanged chunks.
    ids = [
        _make_chunk_id(
            source=chunk.metadata.get("source", "unknown"),
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

    return len(chunks)


def search_knowledge(query: str, k: int = 3):
    """
    Search for the most relevant document chunks.

    This function is for development checks today.
    We'll connect it to the assistant in a later phase.
    """

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    if not 1 <= k <= 10:
        raise ValueError("k must be between 1 and 10")

    vector_store = create_vector_store()

    return vector_store.similarity_search(
        query=query.strip(),
        k=k,
    )
