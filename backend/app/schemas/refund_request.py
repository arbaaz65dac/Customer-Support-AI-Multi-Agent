from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RefundRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    order_id: int
    request_type: str
    reason: str
    status: str
    reviewed_by: int | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime


class RefundReview(BaseModel):
    status: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=2000)
