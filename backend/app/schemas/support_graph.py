
from pydantic import BaseModel, Field


class SupportGraphRequest(BaseModel):
    """Request body for the LangGraph support endpoint."""

    question: str = Field(min_length=1, max_length=2000)


class SupportGraphResponse(BaseModel):
    """Structured response returned by the support graph."""

    answer: str
    intent: str
    selected_agent: str
    sources: list[str] = Field(default_factory=list)
    retrieved_chunks: int = 0
