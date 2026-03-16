"""
MCP Tool: escalate_issue

Updates a ticket's status to escalated and generates a channel-appropriate
holding response to send back to the customer while a human takes over.

Registered as: "escalate_issue"
"""

import logging

from sqlalchemy.orm import Session

from backend.mcp.tool_registry import register

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SLA and team routing tables (mirrors Stage 1 logic, database-aware)
# ---------------------------------------------------------------------------

SLA_BY_SEVERITY: dict[str, str] = {
    "critical": "2 hours",
    "high": "2 hours",
    "medium": "1 business day",
    "low": "2 business days",
}

TEAM_BY_REASON: dict[str, str] = {
    "refund_request": "Billing",
    "pricing_negotiation": "Sales & Account Management",
    "legal_complaint": "Legal & Customer Success",
    "angry_customer": "Senior Customer Success",
    "vip_complaint": "Account Management",
    "security_issue": "Security",
}

ESCALATION_TEMPLATES: dict[str, str] = {
    "email": (
        "Dear {name},\n\n"
        "Thank you for reaching out. I've reviewed your message and I want to ensure "
        "you receive the best possible support for your situation.\n\n"
        "I've escalated your case to our {team} team with {severity} priority. "
        "A team member will be in contact with you within {sla}.\n\n"
        "Reference: {ticket_ref}\n\n"
        "Best regards,\nNexora Customer Success Team"
    ),
    "whatsapp": (
        "Hi {name}! I've flagged your message for our {team} team — "
        "someone will reach out within {sla}. Reference: {ticket_ref}"
    ),
    "web_form": (
        "Thanks for reaching out. I've escalated your case to our {team} team ({severity} priority).\n\n"
        "A team member will contact you within {sla}.\n\n"
        "Reference: {ticket_ref}"
    ),
}


@register("escalate_issue")
def escalate_issue(
    ticket_id: str,
    ticket_ref: str,
    reason: str,
    severity: str,
    channel: str,
    customer_name: str,
    db: Session,
) -> dict:
    """
    Mark a ticket as escalated in the database and generate a holding response.

    Args:
        ticket_id: Internal ticket UUID.
        ticket_ref: Human-readable ticket reference (e.g. TKT-AB12CD34).
        reason: Escalation reason key (e.g. 'refund_request').
        severity: critical | high | medium | low
        channel: email | whatsapp | web_form
        customer_name: Customer's full name for the response.
        db: SQLAlchemy database session.

    Returns:
        dict with escalation confirmation and the holding response text.
    """
    from backend.database import crud

    team = TEAM_BY_REASON.get(reason, "Customer Success")
    sla = SLA_BY_SEVERITY.get(severity, "1 business day")
    first_name = customer_name.split()[0] if customer_name else "there"

    # Update ticket in database
    crud.escalate_ticket(
        db=db,
        ticket_id=ticket_id,
        reason=reason,
        severity=severity,
        assigned_team=team,
    )

    # Generate holding response for the customer's channel
    template = ESCALATION_TEMPLATES.get(channel, ESCALATION_TEMPLATES["web_form"])
    holding_response = template.format(
        name=first_name,
        team=team,
        severity=severity,
        sla=sla,
        ticket_ref=ticket_ref,
    )

    # Stage 3: send Slack/PagerDuty notification to the team here
    # notification_service.notify(team=team, ticket_ref=ticket_ref, severity=severity)

    logger.info(
        "Escalated ticket %s | reason=%s | severity=%s | team=%s",
        ticket_ref, reason, severity, team
    )

    return {
        "escalated": True,
        "ticket_ref": ticket_ref,
        "assigned_team": team,
        "severity": severity,
        "sla": sla,
        "holding_response": holding_response,
        "notification_sent": False,  # Stage 3: real notifications
    }
