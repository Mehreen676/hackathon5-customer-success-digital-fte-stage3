"""
Ticket Schemas — ticket response models (Stage 2)
"""

from datetime import datetime

from pydantic import BaseModel


class TicketOut(BaseModel):
    """Ticket data returned in API responses."""

    ticket_ref: str
    status: str
    priority: str
    escalated: bool
    escalation_reason: str | None = None
    escalation_severity: str | None = None
    assigned_team: str | None = None
    channel: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketListItem(BaseModel):
    """Summary ticket row for list views."""

    ticket_ref: str
    subject: str
    status: str
    priority: str
    escalated: bool
    channel: str
    created_at: datetime

    model_config = {"from_attributes": True}
