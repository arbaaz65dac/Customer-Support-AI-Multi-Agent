
import pytest

from app.agents.intent_router import classify_intent, select_agent


@pytest.mark.parametrize(
    ("question", "expected_intent", "expected_agent"),
    [
        (
            "What is the refund policy?",
            "policy_question",
            "knowledge",
        ),
        (
            "What should I do if my delivery is late?",
            "policy_question",
            "knowledge",
        ),
        (
            "Find products under 2000",
            "product_search",
            "product_order",
        ),
        (
            "Where is my order?",
            "order_status",
            "product_order",
        ),
        (
            "Please create a support ticket",
            "create_ticket",
            "product_order",
        ),
        (
            "Hello there!",
            "general_question",
            "general",
        ),
        (
            "",
            "unknown",
            "general",
        ),
    ],
)
def test_classify_intent_and_select_agent(
    question,
    expected_intent,
    expected_agent,
):
    intent = classify_intent(question)
    agent = select_agent(intent)

    assert intent == expected_intent
    assert agent == expected_agent


def test_whitespace_only_question_is_unknown():
    assert classify_intent("   ") == "unknown"
