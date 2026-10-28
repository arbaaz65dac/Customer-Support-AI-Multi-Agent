
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, SupportTicket
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketResponse,
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
    """Create a support ticket for an existing customer."""

    customer = db.get(Customer, ticket_data.customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    ticket = SupportTicket(
        customer_id=ticket_data.customer_id,
        subject=ticket_data.subject,
        description=ticket_data.description,
        status="open",
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ticket


@router.get("", response_model=list[SupportTicketResponse])
def list_support_tickets(
    customer_id: int = Query(gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List tickets for a customer in the development environment."""

    customer = db.get(Customer, customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    statement = (
        select(SupportTicket)
        .where(SupportTicket.customer_id == customer_id)
        .order_by(SupportTicket.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return db.scalars(statement).all()
