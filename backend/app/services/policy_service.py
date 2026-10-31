import re
from pathlib import Path


KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[2] / "knowledge_base"


def get_return_window_days() -> int:
    """Read the request window from the same versioned policy used by RAG."""
    policy_paths = list(KNOWLEDGE_BASE_DIR.glob("returns_policy_v*.md"))
    if not policy_paths:
        raise FileNotFoundError("No versioned returns policy was found.")

    def version(path: Path) -> tuple[int, ...]:
        match = re.search(r"_v(\d+(?:\.\d+)*)\.md$", path.name)
        if match is None:
            raise ValueError(f"Invalid returns policy filename: {path.name}")
        return tuple(int(part) for part in match.group(1).split("."))

    policy_path = max(
        policy_paths,
        key=version,
    )
    content = policy_path.read_text(encoding="utf-8")
    match = re.search(
        r"^Return window days:\s*(\d+)\s*$",
        content,
        re.MULTILINE | re.IGNORECASE,
    )
    if match is None:
        raise ValueError("The returns policy has no valid return window.")
    days = int(match.group(1))
    if not 1 <= days <= 90:
        raise ValueError(
            "The returns policy window must be between 1 and 90 days."
        )
    return days
