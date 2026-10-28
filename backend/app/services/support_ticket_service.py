
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, SupportTicket
from app.schemas.support_ticket import SupportTicketCreate


def create_support_ticket(
    db: Session,
    ticket_data: SupportTicketCreate,
) -> SupportTicket:
    """Create a ticket for an existing customer."""
    try:
        customer = db.get(Customer, ticket_data.customer_id)

        if customer is None:
            raise ValueError("Customer not found")

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

    except Exception:
        db.rollback()
        raise


def list_customer_tickets(
    db: Session,
    customer_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[SupportTicket]:
    """Return a customer's tickets, newest first."""
    customer = db.get(Customer, customer_id)

    if customer is None:
        raise ValueError("Customer not found")

    statement = (
        select(SupportTicket)
        .where(SupportTicket.customer_id == customer_id)
        .order_by(SupportTicket.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())
