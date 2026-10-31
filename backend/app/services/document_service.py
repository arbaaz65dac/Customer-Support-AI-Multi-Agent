
from pathlib import Path
import re

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
VERSIONED_POLICY_PATTERN = re.compile(
    r"^(?P<policy>[a-z_]+)_v(?P<version>\d+)\.md$",
    re.IGNORECASE,
)


def _policy_metadata(source: str, content: str) -> dict[str, str]:
    """Derive stable policy name/version metadata from the file and header."""
    filename = Path(source).name
    match = VERSIONED_POLICY_PATTERN.fullmatch(filename)
    if match is None:
        raise ValueError(
            f"Knowledge-base documents must use a versioned filename: {filename}"
        )

    version = match.group("version")
    version_header = re.search(
        r"^Policy version:\s*([0-9]+(?:\.[0-9]+)*)\s*$",
        content,
        re.MULTILINE | re.IGNORECASE,
    )
    effective_date = re.search(
        r"^Effective date:\s*(\d{4}-\d{2}-\d{2})\s*$",
        content,
        re.MULTILINE | re.IGNORECASE,
    )
    if version_header is None or effective_date is None:
        raise ValueError(
            f"Version and effective date are required in {filename}"
        )
    if version_header.group(1).split(".", maxsplit=1)[0] != match.group(
        "version"
    ):
        raise ValueError(
            f"Filename and header versions do not match in {filename}"
        )

    return {
        "policy": match.group("policy").lower(),
        "version": version_header.group(1),
        "effective_date": effective_date.group(1),
    }


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
        glob="*_v*.md",
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
    latest_documents = {}
    for document in documents:
        source = document.metadata.get("source")
        if source:
            document.metadata["source"] = Path(source).name
            metadata = _policy_metadata(
                document.metadata["source"],
                document.page_content,
            )
            document.metadata.update(metadata)
            version_key = tuple(
                int(part) for part in metadata["version"].split(".")
            )
            current = latest_documents.get(metadata["policy"])
            if current is None or version_key > current[0]:
                latest_documents[metadata["policy"]] = (
                    version_key,
                    document,
                )

    return [
        entry[1]
        for entry in sorted(
            latest_documents.values(),
            key=lambda item: item[1].metadata["policy"],
        )
    ]


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
