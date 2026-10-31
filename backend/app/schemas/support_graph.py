
from decimal import Decimal

from pydantic import BaseModel, Field


class SupportGraphRequest(BaseModel):
    """Request body for the LangGraph support endpoint."""

    question: str = Field(min_length=1, max_length=2000)


class SupportProduct(BaseModel):
    id: int
    name: str
    description: str | None = None
    category: str = ""
    price: Decimal
    stock: int


class SupportGraphResponse(BaseModel):
    """Structured response returned by the support graph."""

    answer: str
    intent: str
    selected_agent: str
    sources: list[str] = Field(default_factory=list)
    citations: list[dict[str, str]] = Field(default_factory=list)
    products: list[SupportProduct] = Field(default_factory=list)
    retrieved_chunks: int = 0
