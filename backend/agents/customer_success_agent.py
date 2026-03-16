"""
Customer Success Agent — Stage 2 Service Layer

Public interface for the Stage 2 agent. Channel handlers and API endpoints
call run_agent() to process any normalized inbound message.

This module bridges the API layer and the workflow engine, keeping
the HTTP layer clean and the business logic in workflow.py.

Stage 1 prototype (src/agent/customer_success_agent.py) is preserved
as the fallback demo mode and is NOT modified.
"""

import logging

from sqlalchemy.orm import Session

from backend.agents.workflow import process_message
from backend.schemas.message_schema import NormalizedMessage

logger = logging.getLogger(__name__)


def run_agent(normalized: NormalizedMessage, db: Session) -> dict:
    """
    Execute the Stage 2 agent workflow for a normalized inbound message.

    Args:
        normalized: A NormalizedMessage instance from a channel handler.
        db: Active SQLAlchemy session (injected by FastAPI dependency).

    Returns:
        Full workflow result dict (see workflow.process_message for schema).
    """
    logger.info(
        "Agent received message | channel=%s | customer=%s | content_len=%d",
        normalized.channel,
        normalized.customer_id,
        len(normalized.content),
    )

    result = process_message(
        customer_id=normalized.customer_id,
        channel=normalized.channel,
        content=normalized.content,
        db=db,
        customer_name=normalized.customer_name,
        customer_email=normalized.customer_email,
    )

    return result


def run_demo_mode(customer_id: str, channel: str, message: str) -> dict:
    """
    Fallback demo mode — runs the Stage 1 agent without a database.

    Used for testing and demonstration when no database is available.
    Delegates to the original Stage 1 process_message function.

    Args:
        customer_id: Customer external ID.
        channel: email | whatsapp | web_form
        message: Raw customer message text.

    Returns:
        Stage 1 result dict.
    """
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

    try:
        from customer_success_agent import process_message as stage1_process
        logger.info("Running Stage 1 fallback demo for customer=%s", customer_id)
        return stage1_process(customer_id=customer_id, channel=channel, message=message)
    except ImportError as exc:
        logger.warning("Stage 1 fallback unavailable: %s", exc)
        return {
            "success": False,
            "error": "Stage 1 demo mode unavailable",
            "detail": str(exc),
        }
