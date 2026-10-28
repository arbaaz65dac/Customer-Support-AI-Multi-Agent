from fastapi import APIRouter, HTTPException, status

from app.schemas.chat import ChatRequest, ChatResponse
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