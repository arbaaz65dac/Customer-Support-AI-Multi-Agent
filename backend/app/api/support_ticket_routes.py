
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketResponse,
)
from app.services.support_ticket_service import (
    create_support_ticket as create_ticket_service,
    list_customer_tickets,
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
):
    """HTTP endpoint for creating a support ticket."""
    try:
        return create_ticket_service(db, ticket_data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=list[SupportTicketResponse])
def get_customer_tickets(
    customer_id: int = Query(gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List tickets for a customer in the development environment."""
    try:
        return list_customer_tickets(
            db,
            customer_id=customer_id,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
