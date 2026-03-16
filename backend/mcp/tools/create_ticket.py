"""
MCP Tool: create_ticket

Creates a support ticket in the database and returns a summary dict.

Registered as: "create_ticket"
"""

import logging

from sqlalchemy.orm import Session

from backend.mcp.tool_registry import register

logger = logging.getLogger(__name__)


@register("create_ticket")
def create_ticket(
    customer_id: str,
    channel: str,
    subject: str,
    description: str,
    db: Session,
    priority: str = "low",
    status: str = "open",
    conversation_id: str | None = None,
    escalated: bool = False,
    escalation_reason: str | None = None,
    escalation_severity: str | None = None,
    assigned_team: str | None = None,
) -> dict:
    """
    Create a support ticket and persist it to the database.

    Args:
        customer_id: Internal customer UUID.
        channel: Channel the request came through.
        subject: Short description of the issue.
        description: Full message or description body.
        db: SQLAlchemy database session.
        priority: low | medium | high | critical
        status: open | escalated | auto-resolved | pending_review
        conversation_id: Link to the active conversation (optional).
        escalated: Whether the ticket is escalated.
        escalation_reason: Reason key for escalation.
        escalation_severity: Severity level of escalation.
        assigned_team: Team responsible for this ticket.

    Returns:
        dict with ticket_ref, status, priority, escalated, created_at
    """
    from backend.database import crud

    ticket = crud.create_ticket(
        db=db,
        customer_id=customer_id,
        channel=channel,
        subject=subject,
        description=description,
        priority=priority,
        status=status,
        conversation_id=conversation_id,
        escalated=escalated,
        escalation_reason=escalation_reason,
        escalation_severity=escalation_severity,
        assigned_team=assigned_team,
    )

    logger.info(
        "Created ticket %s | %s | %s | escalated=%s",
        ticket.ticket_ref, channel, priority, escalated
    )

    return {
        "ticket_id": ticket.id,
        "ticket_ref": ticket.ticket_ref,
        "status": ticket.status,
        "priority": ticket.priority,
        "escalated": ticket.escalated,
        "channel": ticket.channel,
        "created_at": ticket.created_at.isoformat(),
    }
