"""
SQLAlchemy ORM Models — Customer Success Digital FTE (Stage 2)

PostgreSQL-ready schema. Runs on SQLite in development.

Tables:
    customers               — Customer accounts
    customer_identifiers    — Channel-specific identifiers (email, phone)
    conversations           — Support conversation threads
    messages                — Individual messages within conversations
    tickets                 — Support tickets with lifecycle tracking
    knowledge_base          — Searchable knowledge base entries
    agent_metrics           — Agent performance tracking
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.database import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# customers
# ---------------------------------------------------------------------------

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    external_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200))
    account_tier: Mapped[str] = mapped_column(String(50), default="starter")
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    # Relationships
    identifiers: Mapped[List["CustomerIdentifier"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Customer {self.external_id} | {self.name} | {self.account_tier}>"


# ---------------------------------------------------------------------------
# customer_identifiers
# ---------------------------------------------------------------------------

class CustomerIdentifier(Base):
    """Maps channel-specific identifiers to a customer record.

    Examples:
        channel='email',     identifier='sarah@brightflow.com'
        channel='whatsapp',  identifier='+1-555-0101'
        channel='web_form',  identifier='session:abc123'
    """

    __tablename__ = "customer_identifiers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    identifier: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    customer: Mapped["Customer"] = relationship(back_populates="identifiers")

    def __repr__(self) -> str:
        return f"<CustomerIdentifier {self.channel}:{self.identifier}>"


# ---------------------------------------------------------------------------
# conversations
# ---------------------------------------------------------------------------

class Conversation(Base):
    """A thread of messages between a customer and the support agent."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active / closed / escalated
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    customer: Mapped["Customer"] = relationship(back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    tickets: Mapped[List["Ticket"]] = relationship(back_populates="conversation")

    def __repr__(self) -> str:
        return f"<Conversation {self.id[:8]} | {self.channel} | {self.status}>"


# ---------------------------------------------------------------------------
# messages
# ---------------------------------------------------------------------------

class Message(Base):
    """A single message within a conversation (inbound or agent response)."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # customer / agent
    content: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message [{self.role}] {self.content[:40]}...>"


# ---------------------------------------------------------------------------
# tickets
# ---------------------------------------------------------------------------

class Ticket(Base):
    """A support ticket with full lifecycle tracking."""

    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_ref: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    conversation_id: Mapped[Optional[str]] = mapped_column(ForeignKey("conversations.id"))
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="low")       # low/medium/high/critical
    status: Mapped[str] = mapped_column(String(50), default="open")         # open/escalated/auto-resolved/pending_review/closed
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reason: Mapped[Optional[str]] = mapped_column(String(100))
    escalation_severity: Mapped[Optional[str]] = mapped_column(String(20))
    assigned_team: Mapped[Optional[str]] = mapped_column(String(100))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    customer: Mapped["Customer"] = relationship(back_populates="tickets")
    conversation: Mapped["Conversation"] = relationship(back_populates="tickets")

    def __repr__(self) -> str:
        return f"<Ticket {self.ticket_ref} | {self.priority} | {self.status}>"


# ---------------------------------------------------------------------------
# knowledge_base
# ---------------------------------------------------------------------------

class KnowledgeBaseEntry(Base):
    """A searchable knowledge base article."""

    __tablename__ = "knowledge_base"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    topic: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    keywords: Mapped[str] = mapped_column(Text, nullable=False)  # comma-separated
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="general")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    def __repr__(self) -> str:
        return f"<KBEntry {self.topic} | {self.category}>"


# ---------------------------------------------------------------------------
# agent_metrics
# ---------------------------------------------------------------------------

class AgentMetric(Base):
    """Records performance and outcome data for each agent interaction."""

    __tablename__ = "agent_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tickets.id"))
    conversation_id: Mapped[Optional[str]] = mapped_column(ForeignKey("conversations.id"))
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    intent: Mapped[Optional[str]] = mapped_column(String(100))
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reason: Mapped[Optional[str]] = mapped_column(String(100))
    kb_used: Mapped[bool] = mapped_column(Boolean, default=False)
    kb_topic: Mapped[Optional[str]] = mapped_column(String(100))
    processing_time_ms: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    def __repr__(self) -> str:
        return f"<AgentMetric {self.channel} | escalated={self.escalated} | kb={self.kb_used}>"
