
from pathlib import Path

from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Resolve the knowledge-base directory from this file's location.
# This works even when you start Python from a different directory.
KNOWLEDGE_BASE_DIR = (
    Path(__file__).resolve().parents[2] / "knowledge_base"
)


def load_documents() -> list[Document]:
    """
    Load Markdown files from the local knowledge-base folder.

    Each returned Document contains:
    - page_content: the text read from the file
    - metadata: information about its source
    """

    if not KNOWLEDGE_BASE_DIR.exists():
        raise FileNotFoundError(
            f"Knowledge-base directory not found: {KNOWLEDGE_BASE_DIR}"
        )

    # Read all Markdown files using UTF-8 encoding.
    loader = DirectoryLoader(
        str(KNOWLEDGE_BASE_DIR),
        glob="*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        recursive=False,
        show_progress=False,
        silent_errors=False,
    )

    documents = loader.load()

    if not documents:
        raise ValueError(
            f"No Markdown documents found in {KNOWLEDGE_BASE_DIR}"
        )

    # Keep source metadata but make the source value portable.
    # We store just the filename rather than a machine-specific path.
    for document in documents:
        source = document.metadata.get("source")
        if source:
            document.metadata["source"] = Path(source).name

    return documents


def split_documents(
    documents: list[Document],
) -> list[Document]:
    """
    Split loaded documents into smaller chunks.

    Overlap helps retain context when a relevant passage falls
    near the boundary between two chunks.
    """

    if not documents:
        raise ValueError("Cannot split an empty document list")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        length_function=len,
        separators=["\n## ", "\n# ", "\n\n", "\n", " ", ""],
        add_start_index=True,
    )

    chunks = splitter.split_documents(documents)

    if not chunks:
        raise ValueError("Document splitting produced no chunks")

    return chunks


def load_and_split_documents() -> list[Document]:
    """Convenience function for the complete preparation pipeline."""

    documents = load_documents()
    return split_documents(documents)
