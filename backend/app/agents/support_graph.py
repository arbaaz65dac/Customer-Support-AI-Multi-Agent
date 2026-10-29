
from langgraph.graph import END, START, StateGraph

from app.agents.graph_state import SupportGraphState
from app.agents.intent_router import classify_intent, select_agent

from typing import TypedDict

from langgraph.runtime import Runtime
from sqlalchemy.orm import Session

from app.services.tool_agent_service import answer_with_tools

class SupportGraphContext(TypedDict, total=False):
    """Dependencies supplied at graph invocation time."""

    db: Session

def route_request(state: SupportGraphState) -> dict:
    """Classify the question and select the responsible agent."""

    question = state.get("question", "").strip()
    intent = classify_intent(question)
    selected_agent = select_agent(intent)

    return {
        "intent": intent,
        "selected_agent": selected_agent,
    }



def knowledge_agent(state: SupportGraphState) -> dict:
    """Use the existing RAG service to answer knowledge questions."""

    from app.services.rag_service import answer_from_knowledge

    # Pass the customer's original question to the existing RAG pipeline.
    result = answer_from_knowledge(state["question"])

    # Map the RAG response into the shared LangGraph state.
    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "retrieved_chunks": result.get("retrieved_chunks", 0),
    }



def product_order_agent(
    state: SupportGraphState,
    runtime: Runtime[SupportGraphContext],
) -> dict:
    """Handle product and order questions using existing validated tools."""

    # Database sessions belong in runtime context, not conversation state.
    context = runtime.context or {}
    db = context.get("db")

    # Routing-only tests can run without a database session.
    if db is None:
        return {
            "answer": (
                "The Product & Order Agent was selected, but a database "
                "session is required to perform product or order lookups."
            ),
            "sources": [],
            "retrieved_chunks": 0,
        }

    # Reuse the existing Groq agent and its approved database tools.
    answer = answer_with_tools(
        message=state["question"],
        db=db,
    )

    return {
        "answer": answer,
        "sources": [],
        "retrieved_chunks": 0,
    }


def general_agent(state: SupportGraphState) -> dict:
    """Temporary node for greetings and general questions."""

    return {
        "answer": (
            "General support agent selected. "
            "General response handling will be added later."
        ),
        "sources": [],
        "retrieved_chunks": 0,
    }


def choose_agent(state: SupportGraphState) -> str:
    """Return the next graph node based on the selected agent."""

    return state["selected_agent"]


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

    graph.add_edge(START, "router")

    graph.add_conditional_edges(
        "router",
        choose_agent,
        {
            "knowledge": "knowledge",
            "product_order": "product_order",
            "general": "general",
        },
    )

    graph.add_edge("knowledge", END)
    graph.add_edge("product_order", END)
    graph.add_edge("general", END)

    return graph.compile()


# Compile once and reuse the graph.
support_graph = build_support_graph()
