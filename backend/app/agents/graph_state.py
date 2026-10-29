
from typing import Literal, TypedDict


# Restrict the router to these supported intent categories.
Intent = Literal[
    "policy_question",
    "product_search",
    "order_status",
    "create_ticket",
    "general_question",
    "unknown",
]


# Restrict the graph to the agents we intend to support.
AgentName = Literal[
    "knowledge",
    "product_order",
    "general",
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

    # Number of chunks retrieved by the RAG pipeline.
    retrieved_chunks: int

    # Error message, if a node fails safely.
    error: str
