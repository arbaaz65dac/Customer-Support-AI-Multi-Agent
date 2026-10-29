
from pydantic import BaseModel


class AdminDashboardResponse(BaseModel):
    """Response containing support-ticket dashboard statistics."""

    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
