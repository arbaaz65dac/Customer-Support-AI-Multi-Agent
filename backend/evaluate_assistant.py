"""Evaluate deterministic support routing, policy retrieval, and safe refusals.

Run from the backend directory:
    python evaluate_assistant.py

Run the provider-independent checks only:
    python evaluate_assistant.py --skip-retrieval
"""

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from app.agents.intent_router import classify_intent
from app.agents.support_graph import DOMAIN_REFUSAL, support_graph


BACKEND_DIR = Path(__file__).resolve().parent
DATASET_PATH = BACKEND_DIR / "tests" / "rag_evaluation_cases.json"


def load_evaluation_cases() -> list[dict[str, Any]]:
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        cases = json.load(file)
    if not isinstance(cases, list) or not cases:
        raise ValueError("The evaluation dataset must be a non-empty list.")
    ids = [case.get("id") for case in cases]
    if any(not isinstance(case_id, str) or not case_id for case_id in ids):
        raise ValueError("Every evaluation case must have a non-empty id.")
    if len(set(ids)) != len(ids):
        raise ValueError("Evaluation case ids must be unique.")
    return cases


def evaluate_routing(cases: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    elapsed_ms = 0.0
    for case in cases:
        started = perf_counter()
        actual = classify_intent(case["question"])
        elapsed_ms += (perf_counter() - started) * 1000
        expected = case["expected_intent"]
        results.append(
            {
                "id": case["id"],
                "category": case.get("category", "uncategorized"),
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
            }
        )
    passed = sum(result["passed"] for result in results)
    return {
        "passed": passed,
        "total": len(results),
        "accuracy": passed / len(results),
        "total_latency_ms": elapsed_ms,
        "cases": results,
    }


def evaluate_safe_fallbacks(
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    guarded_cases = [case for case in cases if case.get("expect_refusal")]
    results = []
    elapsed_ms = 0.0
    for case in guarded_cases:
        started = perf_counter()
        result = support_graph.invoke({"question": case["question"]})
        elapsed_ms += (perf_counter() - started) * 1000
        answer = result.get("answer", "")
        passed = (
            result.get("intent") == "out_of_domain"
            and result.get("selected_agent") == "out_of_domain"
            and answer == DOMAIN_REFUSAL
            and not result.get("sources")
            and not result.get("citations")
            and not result.get("products")
        )
        results.append({"id": case["id"], "passed": passed})

    passed = sum(result["passed"] for result in results)
    total = len(results)
    return {
        "passed": passed,
        "total": total,
        "rate": passed / total if total else None,
        "total_latency_ms": elapsed_ms,
        "cases": results,
    }


def evaluate_retrieval(cases: list[dict[str, Any]]) -> dict[str, Any]:
    from app.services.vector_store_service import retrieve_relevant_knowledge

    supported_cases = [
        case
        for case in cases
        if case.get("answer_should_be_supported")
        and case.get("expected_sources")
    ]
    results = []
    elapsed_ms = 0.0
    for case in supported_cases:
        started = perf_counter()
        retrieved = retrieve_relevant_knowledge(case["question"])
        elapsed_ms += (perf_counter() - started) * 1000
        actual_sources = {
            item["document"].metadata.get("source", "unknown")
            for item in retrieved
        }
        expected_sources = set(case["expected_sources"])
        passed = expected_sources.issubset(actual_sources)
        results.append(
            {
                "id": case["id"],
                "expected_sources": sorted(expected_sources),
                "actual_sources": sorted(actual_sources),
                "passed": passed,
            }
        )

    passed = sum(result["passed"] for result in results)
    total = len(results)
    return {
        "passed": passed,
        "total": total,
        "success_rate": passed / total if total else None,
        "total_latency_ms": elapsed_ms,
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-retrieval",
        action="store_true",
        help="Skip Gemini/Chroma retrieval checks and run offline checks only.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable metrics without case detail.",
    )
    args = parser.parse_args()

    cases = load_evaluation_cases()
    report: dict[str, Any] = {
        "case_count": len(cases),
        "routing": evaluate_routing(cases),
        "safe_fallback": evaluate_safe_fallbacks(cases),
        "retrieval": None,
    }
    if not args.skip_retrieval:
        report["retrieval"] = evaluate_retrieval(cases)
    timed_operations = [
        (report["routing"]["total_latency_ms"], report["routing"]["total"]),
        (
            report["safe_fallback"]["total_latency_ms"],
            report["safe_fallback"]["total"],
        ),
    ]
    if report["retrieval"] is not None:
        timed_operations.append(
            (
                report["retrieval"]["total_latency_ms"],
                report["retrieval"]["total"],
            )
        )
    timed_calls = sum(count for _, count in timed_operations)
    average_latency_ms = (
        sum(duration for duration, _ in timed_operations) / timed_calls
        if timed_calls
        else None
    )

    if args.json:
        summary = {
            "case_count": report["case_count"],
            "routing_accuracy": report["routing"]["accuracy"],
            "routing_passed": report["routing"]["passed"],
            "routing_total": report["routing"]["total"],
            "retrieval_success_rate": (
                report["retrieval"]["success_rate"]
                if report["retrieval"]
                else None
            ),
            "retrieval_passed": (
                report["retrieval"]["passed"]
                if report["retrieval"]
                else None
            ),
            "retrieval_total": (
                report["retrieval"]["total"]
                if report["retrieval"]
                else None
            ),
            "safe_fallback_rate": report["safe_fallback"]["rate"],
            "safe_fallback_passed": report["safe_fallback"]["passed"],
            "safe_fallback_total": report["safe_fallback"]["total"],
            "average_latency_ms": average_latency_ms,
        }
        print(json.dumps(summary, indent=2))
    else:
        print(f"Evaluation cases: {report['case_count']}")
        routing = report["routing"]
        print(
            f"Routing accuracy: {routing['passed']}/{routing['total']} "
            f"({routing['accuracy']:.1%})"
        )
        for result in routing["cases"]:
            if not result["passed"]:
                print(
                    f"  FAIL {result['id']}: expected "
                    f"{result['expected']}, got {result['actual']}"
                )

        fallback = report["safe_fallback"]
        fallback_rate = (
            f"{fallback['rate']:.1%}" if fallback["rate"] is not None else "n/a"
        )
        print(
            f"Safe fallback rate: {fallback['passed']}/{fallback['total']} "
            f"({fallback_rate})"
        )
        if average_latency_ms is not None:
            print(
                "Average evaluation operation latency "
                f"(route/refusal/retrieval): {average_latency_ms:.2f} ms"
            )
        for result in fallback["cases"]:
            if not result["passed"]:
                print(f"  FAIL unsafe refusal case: {result['id']}")

        retrieval = report["retrieval"]
        if retrieval is None:
            print("Retrieval success: skipped")
        else:
            print(
                f"Retrieval success: {retrieval['passed']}/"
                f"{retrieval['total']} ({retrieval['success_rate']:.1%})"
            )
            for result in retrieval["cases"]:
                if not result["passed"]:
                    print(
                        f"  FAIL {result['id']}: expected "
                        f"{result['expected_sources']}, got "
                        f"{result['actual_sources']}"
                    )

    checks_passed = (
        report["routing"]["passed"] == report["routing"]["total"]
        and report["safe_fallback"]["passed"]
        == report["safe_fallback"]["total"]
        and (
            report["retrieval"] is None
            or report["retrieval"]["passed"]
            == report["retrieval"]["total"]
        )
    )
    return 0 if checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
