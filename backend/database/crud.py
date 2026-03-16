"""
CRUD Operations — Customer Success Digital FTE (Stage 2)

All database reads and writes go through these functions.
Business logic lives in src/services/ and src/agents/.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.database.models import (
    AgentMetric,
    Conversation,
    Customer,
    CustomerIdentifier,
    KnowledgeBaseEntry,
    Message,
    Ticket,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ticket_ref() -> str:
    return f"TKT-{str(uuid.uuid4())[:8].upper()}"


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

def get_customer_by_external_id(db: Session, external_id: str) -> Customer | None:
    return db.query(Customer).filter(Customer.external_id == external_id).first()


def get_customer_by_identifier(
    db: Session, channel: str, identifier: str
) -> Customer | None:
    """Look up a customer by their channel-specific identifier (e.g. email address)."""
    ci = (
        db.query(CustomerIdentifier)
        .filter(
            CustomerIdentifier.channel == channel,
            CustomerIdentifier.identifier == identifier,
        )
        .first()
    )
    return ci.customer if ci else None


def create_customer(
    db: Session,
    external_id: str,
    name: str = "Valued Customer",
    email: str | None = None,
    account_tier: str = "starter",
    is_vip: bool = False,
) -> Customer:
    customer = Customer(
        external_id=external_id,
        name=name,
        email=email,
        account_tier=account_tier,
        is_vip=is_vip,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_or_create_customer(
    db: Session,
    external_id: str,
    name: str = "Valued Customer",
    email: str | None = None,
    account_tier: str = "starter",
    is_vip: bool = False,
) -> Customer:
    customer = get_customer_by_external_id(db, external_id)
    if customer:
        return customer
    return create_customer(db, external_id, name, email, account_tier, is_vip)


def add_customer_identifier(
    db: Session, customer_id: str, channel: str, identifier: str
) -> CustomerIdentifier:
    existing = (
        db.query(CustomerIdentifier)
        .filter(
            CustomerIdentifier.customer_id == customer_id,
            CustomerIdentifier.channel == channel,
            CustomerIdentifier.identifier == identifier,
        )
        .first()
    )
    if existing:
        return existing
    ci = CustomerIdentifier(customer_id=customer_id, channel=channel, identifier=identifier)
    db.add(ci)
    db.commit()
    db.refresh(ci)
    return ci


def get_all_customers(db: Session, skip: int = 0, limit: int = 100) -> list[Customer]:
    return db.query(Customer).offset(skip).limit(limit).all()


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

def get_active_conversation(
    db: Session, customer_id: str, channel: str
) -> Conversation | None:
    """Return the most recent active conversation for this customer + channel."""
    return (
        db.query(Conversation)
        .filter(
            Conversation.customer_id == customer_id,
            Conversation.channel == channel,
            Conversation.status == "active",
        )
        .order_by(Conversation.started_at.desc())
        .first()
    )


def create_conversation(db: Session, customer_id: str, channel: str) -> Conversation:
    convo = Conversation(customer_id=customer_id, channel=channel, status="active")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


def get_or_create_conversation(
    db: Session, customer_id: str, channel: str
) -> Conversation:
    convo = get_active_conversation(db, customer_id, channel)
    if convo:
        return convo
    return create_conversation(db, customer_id, channel)


def close_conversation(db: Session, conversation_id: str) -> Conversation | None:
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if convo:
        convo.status = "closed"
        db.commit()
        db.refresh(convo)
    return convo


def escalate_conversation(db: Session, conversation_id: str) -> Conversation | None:
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if convo:
        convo.status = "escalated"
        db.commit()
        db.refresh(convo)
    return convo


def get_conversation_by_id(db: Session, conversation_id: str) -> Conversation | None:
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def create_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    channel: str,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        channel=channel,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_conversation_messages(
    db: Session, conversation_id: str
) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------

def create_ticket(
    db: Session,
    customer_id: str,
    channel: str,
    subject: str,
    description: str,
    priority: str = "low",
    status: str = "open",
    conversation_id: str | None = None,
    escalated: bool = False,
    escalation_reason: str | None = None,
    escalation_severity: str | None = None,
    assigned_team: str | None = None,
) -> Ticket:
    ticket = Ticket(
        ticket_ref=_ticket_ref(),
        customer_id=customer_id,
        conversation_id=conversation_id,
        channel=channel,
        subject=subject,
        description=description,
        priority=priority,
        status=status,
        escalated=escalated,
        escalation_reason=escalation_reason,
        escalation_severity=escalation_severity,
        assigned_team=assigned_team,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket_by_ref(db: Session, ticket_ref: str) -> Ticket | None:
    return db.query(Ticket).filter(Ticket.ticket_ref == ticket_ref).first()


def get_ticket_by_id(db: Session, ticket_id: str) -> Ticket | None:
    return db.query(Ticket).filter(Ticket.id == ticket_id).first()


def update_ticket(
    db: Session,
    ticket_id: str,
    **kwargs,
) -> Ticket | None:
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None
    for key, value in kwargs.items():
        if hasattr(ticket, key):
            setattr(ticket, key, value)
    db.commit()
    db.refresh(ticket)
    return ticket


def escalate_ticket(
    db: Session,
    ticket_id: str,
    reason: str,
    severity: str,
    assigned_team: str,
) -> Ticket | None:
    return update_ticket(
        db,
        ticket_id,
        status="escalated",
        escalated=True,
        escalation_reason=reason,
        escalation_severity=severity,
        assigned_team=assigned_team,
    )


def resolve_ticket(db: Session, ticket_id: str) -> Ticket | None:
    return update_ticket(
        db,
        ticket_id,
        status="resolved",
        resolved_at=datetime.now(timezone.utc),
    )


def get_customer_tickets(
    db: Session, customer_id: str, limit: int = 20
) -> list[Ticket]:
    return (
        db.query(Ticket)
        .filter(Ticket.customer_id == customer_id)
        .order_by(Ticket.created_at.desc())
        .limit(limit)
        .all()
    )


def get_all_tickets(
    db: Session, skip: int = 0, limit: int = 50
) -> list[Ticket]:
    return (
        db.query(Ticket)
        .order_by(Ticket.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------

def get_all_kb_entries(db: Session) -> list[KnowledgeBaseEntry]:
    return db.query(KnowledgeBaseEntry).filter(KnowledgeBaseEntry.active == True).all()


def get_kb_entry_by_topic(db: Session, topic: str) -> KnowledgeBaseEntry | None:
    return db.query(KnowledgeBaseEntry).filter(KnowledgeBaseEntry.topic == topic).first()


def create_kb_entry(
    db: Session,
    topic: str,
    keywords: str,
    content: str,
    category: str = "general",
) -> KnowledgeBaseEntry:
    entry = KnowledgeBaseEntry(
        topic=topic, keywords=keywords, content=content, category=category
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def search_kb_entries(
    db: Session, query: str, max_results: int = 3
) -> list[dict]:
    """
    Keyword-score search over the knowledge base.
    Returns a list of dicts with topic, content, and score.
    Works with both SQLite and PostgreSQL.
    """
    entries = get_all_kb_entries(db)
    query_lower = query.lower()
    query_words = set(query_lower.split())

    scored: list[tuple[float, KnowledgeBaseEntry]] = []
    for entry in entries:
        keywords = [kw.strip() for kw in entry.keywords.split(",")]
        match_score = sum(1 for kw in keywords if kw in query_lower)
        keyword_words = set(" ".join(keywords).split())
        word_overlap = len(query_words & keyword_words)
        total = match_score + (word_overlap * 0.5)
        if total > 0:
            scored.append((total, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "topic": e.topic,
            "content": e.content,
            "category": e.category,
            "score": score,
        }
        for score, e in scored[:max_results]
    ]


def count_kb_entries(db: Session) -> int:
    return db.query(KnowledgeBaseEntry).count()


# ---------------------------------------------------------------------------
# Agent Metrics
# ---------------------------------------------------------------------------

def create_metric(
    db: Session,
    channel: str,
    ticket_id: str | None = None,
    conversation_id: str | None = None,
    intent: str | None = None,
    escalated: bool = False,
    escalation_reason: str | None = None,
    kb_used: bool = False,
    kb_topic: str | None = None,
    processing_time_ms: float | None = None,
) -> AgentMetric:
    metric = AgentMetric(
        channel=channel,
        ticket_id=ticket_id,
        conversation_id=conversation_id,
        intent=intent,
        escalated=escalated,
        escalation_reason=escalation_reason,
        kb_used=kb_used,
        kb_topic=kb_topic,
        processing_time_ms=processing_time_ms,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric
