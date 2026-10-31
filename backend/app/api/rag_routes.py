import logging

from fastapi import APIRouter, HTTPException

from app.schemas.rag import RAGRequest, RAGResponse
from app.services.rag_service import answer_from_knowledge
from app.core.structured_logging import log_event


router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"],
)


@router.post("/ask", response_model=RAGResponse)
def ask_knowledge_base(request: RAGRequest):
    """Answer a question using retrieved support documents."""

    try:
        result = answer_from_knowledge(request.question)
        return RAGResponse(**result)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        # Keep internal configuration details out of the HTTP response.
        log_event(
            logging.ERROR,
            "provider_error",
            error_type=type(exc).__name__,
        )

        raise HTTPException(
            status_code=503,
            detail="The RAG service is currently unavailable.",
        ) from exc

    except Exception as exc:
        log_event(
            logging.ERROR,
            "provider_error",
            error_type=type(exc).__name__,
        )

        raise HTTPException(
            status_code=502,
            detail="The RAG service could not generate an answer.",
        ) from exc