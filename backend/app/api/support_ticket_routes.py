
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_customer, require_admin
from app.database import get_db
from app.models import Customer
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketResponse,
    SupportTicketStatusUpdate,
)
from app.services.support_ticket_service import (
    create_support_ticket as create_ticket_service,
    list_customer_tickets,
    list_all_support_tickets,
    update_support_ticket_status,
)


router = APIRouter(
    prefix="/api/support-tickets",
    tags=["Support Tickets"],
)


@router.post(
    "",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_support_ticket(
    ticket_data: SupportTicketCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """Create a ticket for the authenticated customer."""

    try:
        return create_ticket_service(
            db=db,
            ticket_data=ticket_data,
            customer_id=current_customer.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/admin/all",
    response_model=list[SupportTicketResponse],
)
def get_all_support_tickets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    """List all customers' support tickets for administrators only."""

    return list_all_support_tickets(
        db=db,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/{ticket_id}/status",
    response_model=SupportTicketResponse,
)
def update_ticket_status(
    ticket_id: int,
    status_data: SupportTicketStatusUpdate,
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    """Allow administrators to update a support ticket's status."""

    ticket = update_support_ticket_status(
        db=db,
        ticket_id=ticket_id,
        new_status=status_data.status,
    )

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found.",
        )

    return ticket

@router.get(
    "",
    response_model=list[SupportTicketResponse],
)
def get_customer_tickets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """List tickets belonging only to the authenticated customer."""

    try:
        return list_customer_tickets(
            db=db,
            customer_id=current_customer.id,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
