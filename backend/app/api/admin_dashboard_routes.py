
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.database import get_db
from app.models import Customer
from app.schemas.admin_dashboard import AdminDashboardResponse
from app.services.support_ticket_service import (
    get_support_ticket_dashboard_stats,
)


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
