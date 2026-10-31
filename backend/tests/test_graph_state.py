
from app.agents.graph_state import SupportGraphState


def test_graph_state_accepts_a_customer_question():
    state: SupportGraphState = {
        "question": "What is the return policy?"
    }

    assert state["question"] == "What is the return policy?"


def test_graph_state_accepts_routing_information():
    state: SupportGraphState = {
        "question": "Find a laptop",
        "intent": "product_search",
        "selected_agent": "product_order",
    }

    assert state["intent"] == "product_search"
    assert state["selected_agent"] == "product_order"


def test_graph_state_accepts_rag_response_metadata():
    state: SupportGraphState = {
        "question": "What is the delivery policy?",
        "intent": "policy_question",
        "selected_agent": "knowledge",
        "answer": "Please refer to the delivery policy.",
        "sources": ["delivery_policy.md"],
        "citations": [
            {
                "source": "delivery_policy.md",
                "policy": "shipping_policy",
                "version": "1.0",
                "effective_date": "2026-10-31",
                "excerpt": "Delivery timing",
            }
        ],
        "retrieved_chunks": 2,
    }

    assert state["sources"] == ["delivery_policy.md"]
    assert state["citations"][0]["policy"] == "shipping_policy"
    assert state["retrieved_chunks"] == 2
