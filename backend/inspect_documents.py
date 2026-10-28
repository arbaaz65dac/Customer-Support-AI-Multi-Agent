
from app.services.document_service import load_and_split_documents


if __name__ == "__main__":
    chunks = load_and_split_documents()

    print(f"Total chunks created: {len(chunks)}")

    for index, chunk in enumerate(chunks, start=1):
        print("\n" + "=" * 60)
        print(f"Chunk: {index}")
        print(f"Source: {chunk.metadata.get('source')}")
        print(f"Start index: {chunk.metadata.get('start_index')}")
        print(f"Characters: {len(chunk.page_content)}")
        print("Content preview:")
        print(chunk.page_content[:300])
