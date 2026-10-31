
from pydantic import BaseModel


class AdminDashboardResponse(BaseModel):
    """Response containing support-ticket dashboard statistics."""

    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    total_customers: int = 0
    total_orders: int = 0
    revenue: float = 0
