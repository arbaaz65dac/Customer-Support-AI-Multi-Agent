
import re
import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from sqlalchemy.orm import Session

from app.agents.graph_state import SupportGraphState
from app.agents.intent_router import classify_intent, select_agent
from app.services.tool_agent_service import answer_with_tools
from app.core.structured_logging import log_event


DOMAIN_REFUSAL = (
    "Sorry, that's outside my domain. I can help with products, orders, "
    "returns, refunds, shipping, warranty, account help, and support tickets."
)
MAX_GRAPH_STEPS = 6

_POLICY_TERMS = re.compile(
    r"\b(return|refund|shipping|delivery|warranty|policy|exchange|cancel)\b",
    re.IGNORECASE,
)
_CATALOG_ACTIONS = re.compile(
    r"\b(show|find|search|list|recommend|browse|catalogue?|products?)\b",
    re.IGNORECASE,
)
_SUPPORT_ACTIONS = re.compile(
    r"\b(show|find|search|list|recommend|browse|catalogue?|products?|"
    r"track|check (?:my )?order|where is my order|order status|"
    r"create|raise|open (?:a )?(?:support )?ticket)\b",
    re.IGNORECASE,
)


class SupportGraphContext(TypedDict, total=False):
    """Trusted dependencies supplied by the application."""

    db: Session
    customer_id: int


def route_request(state: SupportGraphState) -> dict:
    """Classify the question and select the responsible agent."""

    question = state.get("question", "").strip()
    intent = classify_intent(question)
    selected_agent = select_agent(intent)
    log_event(
        logging.INFO,
        "router_decision",
        intent=intent,
        selected_agent=selected_agent,
    )

    return {
        "intent": intent,
        "selected_agent": selected_agent,
    }


def _is_mixed(state: SupportGraphState) -> bool:
    return state.get("intent") == "mixed"


def _policy_question(question: str) -> str:
    """Keep product-search clauses out of mixed-request policy retrieval."""
    clauses = re.split(r"\b(?:also|and)\b", question, flags=re.IGNORECASE)
    policy_clauses = [
        clause.strip()
        for clause in clauses
        if _POLICY_TERMS.search(clause) and not _CATALOG_ACTIONS.search(clause)
    ]
    return " ".join(policy_clauses) or question


def _support_question(question: str) -> str:
    """Keep policy-only clauses out of the tools agent for mixed requests."""
    clauses = re.split(r"\b(?:also|and)\b", question, flags=re.IGNORECASE)
    support_clauses = [
        clause.strip()
        for clause in clauses
        if _SUPPORT_ACTIONS.search(clause)
        and not _POLICY_TERMS.search(clause)
    ]
    return " ".join(support_clauses) or question


def knowledge_agent(state: SupportGraphState) -> dict:
    """Use the existing RAG service to answer knowledge questions."""

    from app.services.rag_service import answer_from_knowledge

    question = state["question"]
    if _is_mixed(state):
        question = _policy_question(question)
    result = answer_from_knowledge(question)

    output: dict[str, object] = {
        "sources": result.get("sources", []),
        "citations": result.get("citations", []),
        "retrieved_chunks": result.get("retrieved_chunks", 0),
    }
    if _is_mixed(state):
        output["knowledge_answer"] = result["answer"]
    else:
        output["answer"] = result["answer"]
    return output


def product_order_agent(
    state: SupportGraphState,
    runtime: Runtime[SupportGraphContext],
) -> dict:
    """Handle product, order, and support-ticket requests using tools."""

    context = runtime.context or {}
    db = context.get("db")
    customer_id = context.get("customer_id")

    if db is None:
        output: dict[str, object] = {}
        error = "A database session is required to complete this request."
        if _is_mixed(state):
            output["product_order_answer"] = error
        else:
            output["answer"] = error
            output["sources"] = []
            output["retrieved_chunks"] = 0
        return output

    # Customer identity comes from trusted application context.
    # Never infer it from the message or LLM-generated tool arguments.
    question = state["question"]
    if _is_mixed(state):
        question = _support_question(question)
    result = answer_with_tools(
        message=question,
        db=db,
        trusted_customer_id=customer_id,
        include_products=True,
    )
    if not isinstance(result, dict):
        raise RuntimeError("Product agent returned an invalid response")
    answer = result.get("answer", "")
    products = result.get("products", [])

    output: dict[str, object] = {}
    if _is_mixed(state):
        output["product_order_answer"] = answer
        output["products"] = products
    else:
        output["answer"] = answer
        output["sources"] = []
        output["retrieved_chunks"] = 0
        output["products"] = products
    return output


def general_agent(state: SupportGraphState) -> dict:
    """Respond to pleasantries without sending arbitrary text to an LLM."""
    return {
        "answer": (
            "Hello! I can help with products, orders, returns, refunds, "
            "shipping, warranty, account help, and support tickets."
        ),
        "sources": [],
        "retrieved_chunks": 0,
    }


def out_of_domain_agent(state: SupportGraphState) -> dict:
    """Short-circuit unsupported and prompt-injection-style requests."""
    return {
        "answer": DOMAIN_REFUSAL,
        "sources": [],
        "citations": [],
        "retrieved_chunks": 0,
    }


def assemble_mixed_response(state: SupportGraphState) -> dict:
    """Combine policy evidence and product/order results for one response."""
    parts = []
    knowledge_answer = state.get("knowledge_answer", "").strip()
    product_answer = state.get("product_order_answer", "").strip()

    if knowledge_answer:
        parts.append(f"Policy information: {knowledge_answer}")
    if product_answer:
        parts.append(f"Products and order support: {product_answer}")

    return {
        "answer": "\n\n".join(parts) or (
            "I couldn't complete the combined request. Please try again."
        )
    }


def choose_agent(state: SupportGraphState) -> Literal[
    "knowledge", "product_order", "general", "mixed", "out_of_domain"
]:
    """Return the next graph node based on the selected agent."""

    return state["selected_agent"]


def continue_after_knowledge(
    state: SupportGraphState,
) -> Literal["product_order", "end"]:
    return "product_order" if _is_mixed(state) else "end"


def continue_after_product_order(
    state: SupportGraphState,
) -> Literal["assemble", "end"]:
    return "assemble" if _is_mixed(state) else "end"


def build_support_graph():
    """Build and compile the customer support routing graph."""

    graph = StateGraph(
        SupportGraphState,
        context_schema=SupportGraphContext,
    )

    graph.add_node("router", route_request)
    graph.add_node("knowledge", knowledge_agent)
    graph.add_node("product_order", product_order_agent)
    graph.add_node("general", general_agent)
    graph.add_node("out_of_domain", out_of_domain_agent)
    graph.add_node("assemble", assemble_mixed_response)

    graph.add_edge(START, "router")

    graph.add_conditional_edges(
        "router",
        choose_agent,
        {
            "knowledge": "knowledge",
            "product_order": "product_order",
            "general": "general",
            "mixed": "knowledge",
            "out_of_domain": "out_of_domain",
        },
    )

    graph.add_conditional_edges(
        "knowledge",
        continue_after_knowledge,
        {"product_order": "product_order", "end": END},
    )
    graph.add_conditional_edges(
        "product_order",
        continue_after_product_order,
        {"assemble": "assemble", "end": END},
    )
    graph.add_edge("general", END)
    graph.add_edge("out_of_domain", END)
    graph.add_edge("assemble", END)

    return graph.compile()


# Compile once and reuse the graph.
support_graph = build_support_graph()
