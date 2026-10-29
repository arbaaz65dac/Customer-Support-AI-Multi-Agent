
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from app.models import Customer, SupportTicket
from app.schemas.support_ticket import SupportTicketCreate


def create_support_ticket(
    db: Session,
    ticket_data: SupportTicketCreate,
    customer_id: int,
) -> SupportTicket:
    """Create a ticket for the specified authenticated customer."""

    try:
        customer = db.get(Customer, customer_id)

        if customer is None:
            raise ValueError("Customer not found")

        ticket = SupportTicket(
            customer_id=customer.id,
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

def list_all_support_tickets(
    db: Session,
    limit: int = 20,
    offset: int = 0,
) -> list[SupportTicket]:
    """Return all support tickets for administrator review."""

    statement = (
        select(SupportTicket)
        .order_by(SupportTicket.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def update_support_ticket_status(
    db: Session,
    ticket_id: int,
    new_status: str,
) -> SupportTicket | None:
    """Update a ticket's status and return the updated ticket.

    Return None if the ticket does not exist.
    """

    ticket = db.get(SupportTicket, ticket_id)

    if ticket is None:
        return None

    ticket.status = new_status

    db.commit()
    db.refresh(ticket)

    return ticket


def get_support_ticket_dashboard_stats(db: Session) -> dict[str, int]:
    """Return aggregated support-ticket counts for the admin dashboard."""

    statement = select(
        func.count(SupportTicket.id).label("total_tickets"),
        func.count(
            case((SupportTicket.status == "open", 1))
        ).label("open_tickets"),
        func.count(
            case((SupportTicket.status == "in_progress", 1))
        ).label("in_progress_tickets"),
        func.count(
            case((SupportTicket.status == "resolved", 1))
        ).label("resolved_tickets"),
    )

    result = db.execute(statement).one()

    return {
        "total_tickets": result.total_tickets,
        "open_tickets": result.open_tickets,
        "in_progress_tickets": result.in_progress_tickets,
        "resolved_tickets": result.resolved_tickets,
    }
