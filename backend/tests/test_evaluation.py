from evaluate_assistant import (
    evaluate_routing,
    evaluate_safe_fallbacks,
    load_evaluation_cases,
)


def test_evaluation_set_covers_required_cases_and_categories():
    cases = load_evaluation_cases()

    assert len(cases) >= 30
    assert {
        "direct",
        "policy",
        "mixed",
        "ambiguous",
        "out_of_domain",
        "injection",
    }.issubset({case["category"] for case in cases})
    assert sum(case["category"] == "injection" for case in cases) >= 5


def test_evaluation_routing_and_safe_fallback_metrics():
    cases = load_evaluation_cases()

    routing = evaluate_routing(cases)
    safe_fallback = evaluate_safe_fallbacks(cases)

    assert routing["passed"] == routing["total"]
    assert safe_fallback["passed"] == safe_fallback["total"]
    assert safe_fallback["total"] > 0
