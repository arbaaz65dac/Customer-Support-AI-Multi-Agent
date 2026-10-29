
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)


class SupportTicketStatusUpdate(BaseModel):
    """Validate status changes requested by an administrator."""

    status: Literal["open", "in_progress", "resolved"]


class SupportTicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    subject: str
    description: str
    status: str
    created_at: datetime
