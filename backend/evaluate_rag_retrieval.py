
"""
Evaluate RAG retrieval against a small, manually curated dataset.

Run from the backend directory:
    python evaluate_rag_retrieval.py
"""

import json
from pathlib import Path

from app.services.vector_store_service import retrieve_relevant_knowledge


# Locate the evaluation dataset independently of the current working directory.
BACKEND_DIR = Path(__file__).resolve().parent
DATASET_PATH = BACKEND_DIR / "tests" / "rag_evaluation_cases.json"


def load_evaluation_cases():
    """Load test questions and their expected source documents."""
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)



def evaluate_retrieval():
    """Measure source coverage and report unsupported-query retrieval separately."""
    cases = load_evaluation_cases()

    supported_cases = [
        case for case in cases
        if case["answer_should_be_supported"]
    ]
    unsupported_cases = [
        case for case in cases
        if not case["answer_should_be_supported"]
    ]

    supported_passes = 0

    for case in supported_cases:
        results = retrieve_relevant_knowledge(case["question"])

        actual_sources = {
            result["document"].metadata.get("source", "unknown")
            for result in results
        }
        expected_sources = set(case["expected_sources"])

        passed = bool(expected_sources) and expected_sources.issubset(
            actual_sources
        )
        supported_passes += int(passed)

        print(f"\n[{'PASS' if passed else 'FAIL'}] {case['id']}")
        print(f"Question: {case['question']}")
        print(f"Expected sources: {sorted(expected_sources)}")
        print(f"Actual sources:   {sorted(actual_sources)}")

    print("\n--- Unsupported-query retrieval diagnostics ---")

    for case in unsupported_cases:
        results = retrieve_relevant_knowledge(case["question"])
        actual_sources = {
            result["document"].metadata.get("source", "unknown")
            for result in results
        }

        print(f"\n[{case['id']}] {case['question']}")
        print(f"Retrieved chunks: {len(results)}")
        print(f"Retrieved sources: {sorted(actual_sources)}")
        print(
            "Note: answer abstention must be evaluated separately "
            "from retrieval."
        )

    total_supported = len(supported_cases)

    print("\n" + "=" * 55)
    print(
        f"Supported-source coverage: "
        f"{supported_passes}/{total_supported}"
    )

    if total_supported:
        print(
            f"Coverage rate: "
            f"{supported_passes / total_supported:.1%}"
        )



if __name__ == "__main__":
    evaluate_retrieval()
