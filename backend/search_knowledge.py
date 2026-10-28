
from app.services.vector_store_service import search_knowledge


if __name__ == "__main__":
    question = (
        "What should I know before requesting my money back?"
    )

    results = search_knowledge(question, k=3)

    print(f"Question: {question}")
    print(f"Retrieved chunks: {len(results)}")

    for index, document in enumerate(results, start=1):
        print("\n" + "=" * 60)
        print(f"Result: {index}")
        print(f"Source: {document.metadata.get('source')}")
        print(f"Content:\n{document.page_content}")
