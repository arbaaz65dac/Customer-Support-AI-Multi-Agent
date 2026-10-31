
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)
    order_id: int | None = Field(default=None, gt=0)


class SupportTicketStatusUpdate(BaseModel):
    """Validate status changes requested by an administrator."""

    status: Literal["open", "in_progress", "resolved", "closed"]


class SupportTicketAdminUpdate(BaseModel):
    status: Literal["open", "in_progress", "resolved", "closed"] | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    assigned_admin_id: int | None = Field(default=None, gt=0)


class TicketReplyCreate(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


class TicketReplyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author_id: int
    message: str
    created_at: datetime


class SupportTicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    subject: str
    description: str
    status: str
    priority: str = "normal"
    order_id: int | None = None
    assigned_admin_id: int | None = None
    created_at: datetime


class SupportTicketDetailResponse(SupportTicketResponse):
    replies: list[TicketReplyResponse] = Field(default_factory=list)
