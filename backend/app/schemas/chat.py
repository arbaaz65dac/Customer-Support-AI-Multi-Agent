from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    # Restrict the amount of text sent to the model.
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        # Reject strings containing only spaces.
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        return value


class ChatResponse(BaseModel):
    # Plain-text answer returned by the LLM service.
    answer: str



from typing import Literal
from pydantic import BaseModel, Field

class ChatAssistantResponse(BaseModel):
    """A predictable response format for the support assistant."""

    # The category of the user's request.
    intent: Literal[
        "general_question",
        "product_search",
        "order_status",
        "create_ticket",
        "policy_question",
        "unknown",
    ]

    # The natural-language response shown to the user.
    answer: str = Field(min_length=1, max_length=2000)

    # A suggested application action, not an executed action.
    suggested_action: Literal[
        "search_products",
        "check_order",
        "create_support_ticket",
        "retrieve_policy",
        "none",
    ]