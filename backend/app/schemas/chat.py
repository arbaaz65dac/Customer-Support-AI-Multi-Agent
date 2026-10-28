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