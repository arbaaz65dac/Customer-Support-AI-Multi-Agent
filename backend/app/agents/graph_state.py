
from typing import Literal, TypedDict


# Restrict the router to these supported intent categories.
Intent = Literal[
    "policy_question",
    "refund_request",
    "product_search",
    "order_status",
    "create_ticket",
    "account_help",
    "mixed",
    "out_of_domain",
    "general_question",
    "unknown",
]


# Restrict the graph to the agents we intend to support.
AgentName = Literal[
    "knowledge",
    "product_order",
    "general",
    "mixed",
    "out_of_domain",
]


class SupportGraphState(TypedDict, total=False):
    """
    Shared state passed between LangGraph nodes.

    total=False allows nodes to populate fields gradually.
    Each node returns only the fields it updates.
    """

    # Original message submitted by the customer.
    question: str

    # Intent identified by the routing node.
    intent: Intent

    # Agent selected by the router.
    selected_agent: AgentName

    # Final response to return to the customer.
    answer: str

    # Knowledge document filenames used to generate the answer.
    sources: list[str]

    # Versioned policy evidence returned by the knowledge agent.
    citations: list[dict[str, str]]

    # Catalogue results returned by validated product tools.
    products: list[dict[str, object]]

    # Number of chunks retrieved by the RAG pipeline.
    retrieved_chunks: int

    # Intermediate outputs used only to assemble mixed requests.
    knowledge_answer: str
    product_order_answer: str

    # Error message, if a node fails safely.
    error: str
