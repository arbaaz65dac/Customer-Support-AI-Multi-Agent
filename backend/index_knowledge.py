
from app.services.vector_store_service import index_knowledge_documents


if __name__ == "__main__":
    # This may call the Gemini API and consume embedding quota.
    try:
        count = index_knowledge_documents()
        print(f"Successfully indexed {count} document chunks.")
    except Exception as exc:
        # Development-only diagnostic. Never print API keys.
        print(f"Indexing failed: {type(exc).__name__}: {exc}")
        raise
