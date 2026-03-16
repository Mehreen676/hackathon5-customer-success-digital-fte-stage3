"""
MCP Tool: get_customer_context

Retrieves a customer's full profile and recent history from the database.
Falls back gracefully if the customer is not found (guest profile).

Registered as: "get_customer_context"
"""

import logging

from sqlalchemy.orm import Session

from backend.mcp.tool_registry import register

logger = logging.getLogger(__name__)


@register("get_customer_context")
def get_customer_context(customer_id: str, db: Session) -> dict:
    """
    Retrieve customer profile and recent ticket history.

    Args:
        customer_id: The customer's internal UUID or external_id.
        db: SQLAlchemy database session.

    Returns:
        dict with customer profile, ticket history, and conversation summary.
        Returns a guest profile dict if the customer is not found.
    """
    from backend.database import crud

    # Try by internal UUID first, then by external_id
    customer = None
    if len(customer_id) == 36 and "-" in customer_id:
        from backend.database.models import Customer
        customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        customer = crud.get_customer_by_external_id(db, customer_id)

    if not customer:
        logger.info("Customer not found: %s — returning guest profile", customer_id)
        return {
            "found": False,
            "id": None,
            "external_id": customer_id,
            "name": "Valued Customer",
            "email": None,
            "account_tier": "unknown",
            "is_vip": False,
            "ticket_count": 0,
            "recent_tickets": [],
        }

    # Fetch recent tickets
    recent_tickets = crud.get_customer_tickets(db, customer.id, limit=5)
    ticket_summaries = [
        {
            "ticket_ref": t.ticket_ref,
            "subject": t.subject,
            "status": t.status,
            "priority": t.priority,
            "created_at": t.created_at.isoformat(),
        }
        for t in recent_tickets
    ]

    logger.info(
        "Retrieved context for customer %s | %s | %s | tickets=%d",
        customer.external_id, customer.name, customer.account_tier, len(recent_tickets)
    )

    return {
        "found": True,
        "id": customer.id,
        "external_id": customer.external_id,
        "name": customer.name,
        "email": customer.email,
        "account_tier": customer.account_tier,
        "is_vip": customer.is_vip,
        "ticket_count": len(recent_tickets),
        "recent_tickets": ticket_summaries,
    }
