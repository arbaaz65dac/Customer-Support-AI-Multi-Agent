
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from sqlalchemy.orm import Session

from app.agents.graph_state import SupportGraphState
from app.agents.intent_router import classify_intent, select_agent
from app.core.config import GROQ_API_KEY, GROQ_MODEL
from app.services.tool_agent_service import answer_with_tools


class SupportGraphContext(TypedDict, total=False):
    """Trusted dependencies supplied by the application."""

    db: Session
    customer_id: int


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

    result = answer_from_knowledge(state["question"])

    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "retrieved_chunks": result.get("retrieved_chunks", 0),
    }


def product_order_agent(
    state: SupportGraphState,
    runtime: Runtime[SupportGraphContext],
) -> dict:
    """Handle product, order, and support-ticket requests using tools."""

    context = runtime.context or {}
    db = context.get("db")
    customer_id = context.get("customer_id")

    if db is None:
        return {
            "answer": (
                "A database session is required to complete this request."
            ),
            "sources": [],
            "retrieved_chunks": 0,
        }

    # Customer identity comes from trusted application context.
    # Never infer it from the message or LLM-generated tool arguments.
    answer = answer_with_tools(
        message=state["question"],
        db=db,
        trusted_customer_id=customer_id,
    )

    return {
        "answer": answer,
        "sources": [],
        "retrieved_chunks": 0,
    }


def general_agent(state: SupportGraphState) -> dict:
    """Generate a helpful response for general customer questions."""

    if not GROQ_API_KEY:
        return {
            "answer": (
                "The AI response service is not configured right now. "
                "Please try again later."
            ),
            "sources": [],
            "retrieved_chunks": 0,
        }

    llm = ChatGroq(
        model=GROQ_MODEL,
        temperature=0.3,
        max_tokens=500,
        api_key=GROQ_API_KEY,
        timeout=30,
        max_retries=1,
    )

    messages = [
        SystemMessage(
            content=(
                "You are a friendly customer support assistant. "
                "Answer greetings and general questions politely and "
                "concisely. Do not invent product details, prices, "
                "order information, company policies, or ticket status. "
                "For information requiring a database lookup or company "
                "policy, explain that you can help check the relevant "
                "information instead of guessing."
            )
        ),
        HumanMessage(content=state["question"]),
    ]

    try:
        response = llm.invoke(messages)

        if isinstance(response.content, str) and response.content.strip():
            answer = response.content.strip()
        else:
            answer = (
                "I'm sorry, I couldn't generate a response just now. "
                "Please try again."
            )

    except Exception:
        # Avoid exposing API keys, provider responses, or internal errors.
        answer = (
            "I'm having trouble responding right now. "
            "Please try again in a moment."
        )

    return {
        "answer": answer,
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
