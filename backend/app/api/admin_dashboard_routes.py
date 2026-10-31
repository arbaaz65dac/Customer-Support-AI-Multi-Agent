
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.database import get_db
from app.models import Customer
from app.schemas.admin_dashboard import AdminDashboardResponse
from app.services.support_ticket_service import (
    get_support_ticket_dashboard_stats,
)
from app.models import Customer, RefundRequest
from app.schemas.refund_request import RefundReview, RefundRequestResponse


router = APIRouter(
    prefix="/api/admin",
    tags=["Admin Dashboard"],
)


@router.get(
    "/dashboard",
    response_model=AdminDashboardResponse,
)
def get_admin_dashboard(
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    """Return support-ticket statistics for administrators only."""

    return get_support_ticket_dashboard_stats(db)


@router.get("/refund-requests", response_model=list[RefundRequestResponse])
def list_refund_requests(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    return db.query(RefundRequest).order_by(
        RefundRequest.created_at.desc()
    ).offset(offset).limit(limit).all()


@router.patch(
    "/refund-requests/{request_id}",
    response_model=RefundRequestResponse,
)
def review_refund_request(
    request_id: int,
    review: RefundReview,
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    refund_request = db.get(RefundRequest, request_id)
    if refund_request is None:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if refund_request.status != "pending":
        raise HTTPException(
            status_code=409, detail="This refund request has already been reviewed."
        )
    refund_request.status = review.status
    refund_request.review_note = review.review_note
    refund_request.reviewed_by = admin_customer.id
    db.commit()
    db.refresh(refund_request)
    return refund_request
