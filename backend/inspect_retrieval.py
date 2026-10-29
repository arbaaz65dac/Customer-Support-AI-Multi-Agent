
from app.services.vector_store_service import create_vector_store


def inspect_query(query: str, k: int = 5):
    """Print candidate chunks and their Chroma distance scores."""

    vector_store = create_vector_store()

    # Chroma returns (document, distance) pairs.
    results = vector_store.similarity_search_with_score(
        query=query,
        k=k,
    )

    print(f"\nQuestion: {query}")
    print(f"Candidates: {len(results)}")

    for rank, (document, distance) in enumerate(results, start=1):
        print("\n" + "-" * 60)
        print(f"Rank: {rank}")
        print(f"Distance: {float(distance):.4f}")
        print(f"Source: {document.metadata.get('source', 'unknown')}")
        print(f"Text: {document.page_content[:250]}")


if __name__ == "__main__":
    inspect_query(
        "What should I do if my delivery is late?"
    )
    inspect_query(
        "How long does a refund take?"
    )
    inspect_query(
        "Does the company deliver to Antarctica?"
    )
