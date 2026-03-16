"""
Conversation Service — Customer Success Digital FTE (Stage 2)

Business logic for conversation thread management.
Provides conversation history retrieval and summarization.
"""

import logging

from sqlalchemy.orm import Session

from backend.database import crud
from backend.database.models import Conversation

logger = logging.getLogger(__name__)


def get_conversation_history(db: Session, conversation_id: str) -> dict:
    """
    Return the full message history for a conversation.

    Args:
        db: Database session.
        conversation_id: Conversation UUID.

    Returns:
        dict with conversation metadata and message list.
    """
    convo = crud.get_conversation_by_id(db, conversation_id)
    if not convo:
        return {"found": False, "messages": []}

    messages = crud.get_conversation_messages(db, conversation_id)

    return {
        "found": True,
        "conversation_id": convo.id,
        "channel": convo.channel,
        "status": convo.status,
        "started_at": convo.started_at.isoformat(),
        "message_count": len(messages),
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


def get_customer_conversations(db: Session, customer_external_id: str) -> list[dict]:
    """Return all conversations for a customer."""
    customer = crud.get_customer_by_external_id(db, customer_external_id)
    if not customer:
        return []

    convos = (
        db.query(Conversation)
        .filter(Conversation.customer_id == customer.id)
        .order_by(Conversation.started_at.desc())
        .limit(20)
        .all()
    )

    return [
        {
            "conversation_id": c.id,
            "channel": c.channel,
            "status": c.status,
            "started_at": c.started_at.isoformat(),
        }
        for c in convos
    ]


def store_turn(
    db: Session,
    conversation_id: str,
    customer_content: str,
    agent_response: str,
    channel: str,
) -> None:
    """
    Store a full conversation turn (customer message + agent response).
    Convenience wrapper used by the workflow.
    """
    crud.create_message(db, conversation_id, "customer", customer_content, channel)
    crud.create_message(db, conversation_id, "agent", agent_response, channel)
    logger.debug("Stored conversation turn in %s", conversation_id)
