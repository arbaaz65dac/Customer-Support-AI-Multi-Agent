from fastapi import APIRouter, HTTPException, status, Depends

from app.schemas.chat import ChatRequest, ChatResponse, ChatAssistantResponse
from app.services.llm_service import generate_answer

router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"],
)


@router.post("/ask", response_model=ChatResponse)
def ask_question(request: ChatRequest):
    """
    Accept a message, pass it to the LLM service,
    and return the generated answer.
    """

    try:
        answer = generate_answer(request.message)

        return ChatResponse(answer=answer)

    except RuntimeError as exc:
        # Configuration or response problems can make the
        # LLM service temporarily unavailable.
        # Log the internal error in a production application.
        print(f"LLM service configuration/runtime error: {exc}")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI service is currently unavailable.",
        ) from exc

    except Exception as exc:
        # Do not expose provider error details or secrets to clients.
        # Replace print with structured logging before production.
        print(f"LLM provider request failed: {type(exc).__name__}")

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service could not generate a response.",
        ) from exc  

from app.services.structured_chat_service import (
    generate_structured_answer,
)

@router.post(
    "/structured",
    response_model=ChatAssistantResponse,
)
def ask_structured_question(request: ChatRequest):
    """Return the answer, intent, and suggested action."""

    try:
        return generate_structured_answer(request.message)

    except RuntimeError as exc:
        print(f"Structured LLM service error: {exc}")

        raise HTTPException(
            status_code=503,
            detail="The AI service is currently unavailable.",
        ) from exc

    except Exception as exc:
        # Log only the exception type to avoid exposing provider details.
        print(f"Structured LLM request failed: {type(exc).__name__}")

        raise HTTPException(
            status_code=502,
            detail="The AI service could not generate a response.",
        ) from exc

from app.database import get_db
from app.services.tool_agent_service import answer_with_tools
from sqlalchemy.orm import Session

@router.post("/agent", response_model=ChatResponse)
def chat_with_tools(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """Answer using approved read-only product/order tools."""

    try:
        answer = answer_with_tools(request.message, db)
        return ChatResponse(answer=answer)

    except RuntimeError as exc:
        print(f"Tool agent runtime error: {exc}")

        raise HTTPException(
            status_code=503,
            detail="The AI service is currently unavailable.",
        ) from exc

    except Exception as exc:
        print(f"Tool agent request failed: {type(exc).__name__}")

        raise HTTPException(
            status_code=502,
            detail="The AI service could not generate a response.",
        ) from exc