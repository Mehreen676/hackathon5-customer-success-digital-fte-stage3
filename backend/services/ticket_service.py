"""
Ticket Service — Customer Success Digital FTE (Stage 2)

Business logic for ticket lifecycle management.
Wraps CRUD operations with validation and business rules.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.database import crud
from backend.database.models import Ticket

logger = logging.getLogger(__name__)

VALID_STATUSES = {"open", "escalated", "auto-resolved", "pending_review", "closed"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}


def get_ticket(db: Session, ticket_ref: str) -> Ticket | None:
    """Retrieve a ticket by its human-readable reference."""
    return crud.get_ticket_by_ref(db, ticket_ref)


def list_customer_tickets(db: Session, customer_external_id: str) -> list[dict]:
    """Return a list of ticket summaries for a customer."""
    customer = crud.get_customer_by_external_id(db, customer_external_id)
    if not customer:
        return []

    tickets = crud.get_customer_tickets(db, customer.id)
    return [
        {
            "ticket_ref": t.ticket_ref,
            "subject": t.subject,
            "status": t.status,
            "priority": t.priority,
            "channel": t.channel,
            "escalated": t.escalated,
            "created_at": t.created_at.isoformat(),
        }
        for t in tickets
    ]


def close_ticket(db: Session, ticket_ref: str) -> dict:
    """Close a ticket and record resolution time."""
    ticket = crud.get_ticket_by_ref(db, ticket_ref)
    if not ticket:
        return {"success": False, "error": f"Ticket {ticket_ref} not found"}

    if ticket.status == "closed":
        return {"success": False, "error": "Ticket is already closed"}

    crud.update_ticket(
        db,
        ticket.id,
        status="closed",
        resolved_at=datetime.now(timezone.utc),
    )

    logger.info("Closed ticket %s", ticket_ref)
    return {"success": True, "ticket_ref": ticket_ref, "status": "closed"}


def get_open_tickets(db: Session, limit: int = 50) -> list[dict]:
    """Return all open (non-closed) tickets ordered by priority."""
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    tickets = crud.get_all_tickets(db, limit=limit)
    open_tickets = [t for t in tickets if t.status != "closed"]
    open_tickets.sort(key=lambda t: priority_order.get(t.priority, 9))

    return [
        {
            "ticket_ref": t.ticket_ref,
            "customer_id": t.customer_id,
            "subject": t.subject,
            "status": t.status,
            "priority": t.priority,
            "channel": t.channel,
            "escalated": t.escalated,
            "assigned_team": t.assigned_team,
            "created_at": t.created_at.isoformat(),
        }
        for t in open_tickets
    ]
