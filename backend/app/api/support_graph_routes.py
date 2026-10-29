
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.support_graph import support_graph
from app.core.security import get_current_customer
from app.database import get_db
from app.models import Customer
from app.schemas.support_graph import (
    SupportGraphRequest,
    SupportGraphResponse,
)


router = APIRouter(
    prefix="/api/support",
    tags=["Multi-Agent Support"],
)


@router.post("/ask", response_model=SupportGraphResponse)
def ask_support_graph(
    request: SupportGraphRequest,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """Route an authenticated customer's question through LangGraph."""

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question cannot be empty.",
        )

    try:
        result = support_graph.invoke(
            {"question": question},
            context={
                "db": db,
                "customer_id": current_customer.id,
            },
        )

        return SupportGraphResponse(
            answer=result.get("answer", ""),
            intent=result.get("intent", "unknown"),
            selected_agent=result.get("selected_agent", "general"),
            sources=result.get("sources", []),
            retrieved_chunks=result.get("retrieved_chunks", 0),
        )

    except RuntimeError as exc:
        print(f"Support graph runtime error: {type(exc).__name__}")

        raise HTTPException(
            status_code=503,
            detail="The support assistant is currently unavailable.",
        ) from exc

    except Exception as exc:
        print(f"Support graph request failed: {type(exc).__name__}")

        raise HTTPException(
            status_code=502,
            detail="The support assistant could not process the request.",
        ) from exc
