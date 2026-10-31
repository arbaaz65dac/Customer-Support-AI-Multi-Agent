
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import chat_rate_limiter
from app.core.structured_logging import log_event
from app.core.security import get_current_customer
from app.database import get_db
from app.models import Customer
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatAssistantResponse,
)
from app.services.llm_service import generate_answer
from app.services.structured_chat_service import (
    generate_structured_answer,
)
from app.services.tool_agent_service import answer_with_tools


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"],
)


@router.post("/ask", response_model=ChatResponse)
def ask_question(request: ChatRequest, http_request: Request):
    """Generate a general LLM answer."""

    client_ip = http_request.client.host if http_request.client else "unknown"
    chat_rate_limiter.check(f"ip:{client_ip}")

    try:
        answer = generate_answer(request.message)
        return ChatResponse(answer=answer)

    except RuntimeError as exc:
        log_event(
            logging.ERROR,
            "provider_error",
            error_type=type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI service is currently unavailable.",
        ) from exc

    except Exception as exc:
        log_event(
            logging.ERROR,
            "provider_error",
            error_type=type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service could not generate a response.",
        ) from exc


@router.post(
    "/structured",
    response_model=ChatAssistantResponse,
)
def ask_structured_question(request: ChatRequest, http_request: Request):
    """Return an answer with intent and suggested action."""

    client_ip = http_request.client.host if http_request.client else "unknown"
    chat_rate_limiter.check(f"ip:{client_ip}")

    try:
        return generate_structured_answer(request.message)

    except RuntimeError as exc:
        log_event(
            logging.ERROR,
            "provider_error",
            error_type=type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI service is currently unavailable.",
        ) from exc

    except Exception as exc:
        log_event(
            logging.ERROR,
            "provider_error",
            error_type=type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service could not generate a response.",
        ) from exc


@router.post("/agent", response_model=ChatResponse)
def chat_with_tools(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """Answer using approved tools and the authenticated customer identity."""

    chat_rate_limiter.check(f"user:{current_customer.id}")

    try:
        answer = answer_with_tools(
            message=request.message,
            db=db,
            trusted_customer_id=current_customer.id,
        )

        return ChatResponse(answer=answer)

    except RuntimeError as exc:
        log_event(
            logging.ERROR,
            "provider_error",
            error_type=type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI service is currently unavailable.",
        ) from exc

    except Exception as exc:
        log_event(
            logging.ERROR,
            "provider_error",
            error_type=type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service could not process the request.",
        ) from exc
