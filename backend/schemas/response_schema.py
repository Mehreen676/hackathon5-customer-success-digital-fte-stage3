"""
Response Schemas — API response envelope models (Stage 3)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.schemas.ticket_schema import TicketOut


class AgentResponse(BaseModel):
    """Full agent response envelope returned by all /support/* endpoints."""

    success: bool
    channel: str
    customer: str
    intent: str | None = None
    escalated: bool
    escalation_reason: str | None = None
    escalation_severity: str | None = None
    kb_used: bool
    kb_topic: str | None = None
    ticket: TicketOut
    response: str
    conversation_id: str


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str
    version: str
    stage: str
    db: str


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    success: bool = False
    error: str
    detail: str | None = None


class TicketStatusResponse(BaseModel):
    """
    Response for GET /support/ticket/{ticket_ref}.

    Returned when a customer looks up a ticket by its reference number.
    Contains enough information to show current status without exposing
    internal database IDs.
    """

    ticket_ref: str
    status: str
    priority: str
    escalated: bool
    channel: str
    subject: str
    created_at: datetime
    customer_name: str
    assigned_team: Optional[str] = None
    escalation_reason: Optional[str] = None
    latest_response: Optional[str] = None

    model_config = {"from_attributes": True}
