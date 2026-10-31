from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.security import get_current_customer
from app.database import get_db
from app.models import Customer, RefundRequest
from app.schemas.refund_request import RefundRequestResponse
from app.services.refund_service import create_refund_request as create_request


router = APIRouter(prefix="/api/refund-requests", tags=["Refund Requests"])


class RefundRequestCreate(BaseModel):
    order_id: int = Field(gt=0)
    request_type: Literal["return", "refund"]
    reason: str = Field(min_length=5, max_length=5000)


@router.post(
    "",
    response_model=RefundRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_refund_request(
    request: RefundRequestCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    try:
        return create_request(
            db=db,
            customer_id=current_customer.id,
            order_id=request.order_id,
            request_type=request.request_type,
            reason=request.reason.strip(),
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message == "Order not found." else 409
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("", response_model=list[RefundRequestResponse])
def list_my_refund_requests(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    return db.scalars(
        select(RefundRequest)
        .where(RefundRequest.customer_id == current_customer.id)
        .order_by(RefundRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
