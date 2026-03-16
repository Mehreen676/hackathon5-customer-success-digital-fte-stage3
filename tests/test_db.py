"""
Database CRUD Tests — Customer Success Digital FTE (Stage 2)

Tests database operations using an isolated in-memory SQLite database.
Covers: customers, conversations, messages, tickets, knowledge base, metrics.

Run with:
    pytest tests/test_db.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.database import Base
from backend.database import crud, models  # noqa: F401


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db():
    """Fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# Customer CRUD tests
# ---------------------------------------------------------------------------

class TestCustomerCRUD:

    def test_create_customer(self, db):
        customer = crud.create_customer(
            db, external_id="CUST-TEST", name="Test User",
            email="test@example.com", account_tier="growth"
        )
        assert customer.id is not None
        assert customer.external_id == "CUST-TEST"
        assert customer.name == "Test User"

    def test_get_customer_by_external_id(self, db):
        crud.create_customer(db, external_id="CUST-FIND", name="Find Me")
        found = crud.get_customer_by_external_id(db, "CUST-FIND")
        assert found is not None
        assert found.name == "Find Me"

    def test_get_customer_not_found_returns_none(self, db):
        result = crud.get_customer_by_external_id(db, "CUST-NONEXISTENT")
        assert result is None

    def test_get_or_create_creates_new(self, db):
        customer = crud.get_or_create_customer(db, "CUST-NEW", name="New Customer")
        assert customer.external_id == "CUST-NEW"

    def test_get_or_create_returns_existing(self, db):
        c1 = crud.create_customer(db, external_id="CUST-EXIST", name="Existing")
        c2 = crud.get_or_create_customer(db, "CUST-EXIST", name="Different Name")
        assert c1.id == c2.id
        assert c2.name == "Existing"  # original name preserved

    def test_vip_customer_flag(self, db):
        customer = crud.create_customer(
            db, external_id="CUST-VIP", name="VIP User",
            account_tier="enterprise", is_vip=True
        )
        assert customer.is_vip is True
        assert customer.account_tier == "enterprise"

    def test_add_customer_identifier(self, db):
        customer = crud.create_customer(db, external_id="CUST-ID", name="ID Test")
        ci = crud.add_customer_identifier(
            db, customer.id, "email", "test@example.com"
        )
        assert ci.channel == "email"
        assert ci.identifier == "test@example.com"

    def test_get_customer_by_identifier(self, db):
        customer = crud.create_customer(db, external_id="CUST-LOOKUP", name="Lookup User")
        crud.add_customer_identifier(db, customer.id, "whatsapp", "+1-555-1234")
        found = crud.get_customer_by_identifier(db, "whatsapp", "+1-555-1234")
        assert found is not None
        assert found.external_id == "CUST-LOOKUP"


# ---------------------------------------------------------------------------
# Conversation CRUD tests
# ---------------------------------------------------------------------------

class TestConversationCRUD:

    def test_create_conversation(self, db):
        customer = crud.create_customer(db, external_id="CUST-CV1", name="Convo User")
        convo = crud.create_conversation(db, customer.id, "email")
        assert convo.id is not None
        assert convo.channel == "email"
        assert convo.status == "active"

    def test_get_active_conversation(self, db):
        customer = crud.create_customer(db, external_id="CUST-CV2", name="Active User")
        crud.create_conversation(db, customer.id, "whatsapp")
        found = crud.get_active_conversation(db, customer.id, "whatsapp")
        assert found is not None
        assert found.status == "active"

    def test_get_or_create_conversation_returns_existing(self, db):
        customer = crud.create_customer(db, external_id="CUST-CV3", name="Return User")
        c1 = crud.create_conversation(db, customer.id, "web_form")
        c2 = crud.get_or_create_conversation(db, customer.id, "web_form")
        assert c1.id == c2.id

    def test_close_conversation(self, db):
        customer = crud.create_customer(db, external_id="CUST-CV4", name="Close User")
        convo = crud.create_conversation(db, customer.id, "email")
        closed = crud.close_conversation(db, convo.id)
        assert closed.status == "closed"

    def test_escalate_conversation(self, db):
        customer = crud.create_customer(db, external_id="CUST-CV5", name="Esc User")
        convo = crud.create_conversation(db, customer.id, "email")
        escalated = crud.escalate_conversation(db, convo.id)
        assert escalated.status == "escalated"


# ---------------------------------------------------------------------------
# Message CRUD tests
# ---------------------------------------------------------------------------

class TestMessageCRUD:

    def test_create_message(self, db):
        customer = crud.create_customer(db, external_id="CUST-MSG1", name="Msg User")
        convo = crud.create_conversation(db, customer.id, "email")
        msg = crud.create_message(db, convo.id, "customer", "Hello, I need help", "email")
        assert msg.id is not None
        assert msg.role == "customer"
        assert msg.content == "Hello, I need help"

    def test_get_conversation_messages(self, db):
        customer = crud.create_customer(db, external_id="CUST-MSG2", name="History User")
        convo = crud.create_conversation(db, customer.id, "whatsapp")
        crud.create_message(db, convo.id, "customer", "First message", "whatsapp")
        crud.create_message(db, convo.id, "agent", "First response", "whatsapp")
        crud.create_message(db, convo.id, "customer", "Follow up", "whatsapp")

        messages = crud.get_conversation_messages(db, convo.id)
        assert len(messages) == 3
        assert messages[0].role == "customer"
        assert messages[1].role == "agent"

    def test_messages_ordered_by_time(self, db):
        customer = crud.create_customer(db, external_id="CUST-MSG3", name="Order User")
        convo = crud.create_conversation(db, customer.id, "email")
        for i in range(5):
            crud.create_message(db, convo.id, "customer", f"Message {i}", "email")
        messages = crud.get_conversation_messages(db, convo.id)
        contents = [m.content for m in messages]
        assert contents == ["Message 0", "Message 1", "Message 2", "Message 3", "Message 4"]


# ---------------------------------------------------------------------------
# Ticket CRUD tests
# ---------------------------------------------------------------------------

class TestTicketCRUD:

    def test_create_ticket(self, db):
        customer = crud.create_customer(db, external_id="CUST-TK1", name="Ticket User")
        ticket = crud.create_ticket(
            db,
            customer_id=customer.id,
            channel="email",
            subject="Password reset",
            description="Cannot log in",
            priority="low",
        )
        assert ticket.id is not None
        assert ticket.ticket_ref.startswith("TKT-")
        assert ticket.priority == "low"

    def test_ticket_ref_is_unique(self, db):
        customer = crud.create_customer(db, external_id="CUST-TK2", name="Unique User")
        t1 = crud.create_ticket(db, customer.id, "email", "Sub1", "Desc1")
        t2 = crud.create_ticket(db, customer.id, "email", "Sub2", "Desc2")
        assert t1.ticket_ref != t2.ticket_ref

    def test_get_ticket_by_ref(self, db):
        customer = crud.create_customer(db, external_id="CUST-TK3", name="Find Ticket User")
        ticket = crud.create_ticket(db, customer.id, "whatsapp", "Help", "Need help")
        found = crud.get_ticket_by_ref(db, ticket.ticket_ref)
        assert found is not None
        assert found.id == ticket.id

    def test_update_ticket(self, db):
        customer = crud.create_customer(db, external_id="CUST-TK4", name="Update User")
        ticket = crud.create_ticket(db, customer.id, "email", "Subject", "Description")
        updated = crud.update_ticket(db, ticket.id, status="closed", priority="high")
        assert updated.status == "closed"
        assert updated.priority == "high"

    def test_escalate_ticket(self, db):
        customer = crud.create_customer(db, external_id="CUST-TK5", name="Escalate User")
        ticket = crud.create_ticket(db, customer.id, "email", "Refund", "I want a refund")
        escalated = crud.escalate_ticket(
            db, ticket.id, "refund_request", "medium", "Billing"
        )
        assert escalated.escalated is True
        assert escalated.status == "escalated"
        assert escalated.escalation_reason == "refund_request"
        assert escalated.assigned_team == "Billing"

    def test_get_customer_tickets(self, db):
        customer = crud.create_customer(db, external_id="CUST-TK6", name="Multi Ticket User")
        for i in range(3):
            crud.create_ticket(db, customer.id, "email", f"Sub {i}", f"Desc {i}")
        tickets = crud.get_customer_tickets(db, customer.id)
        assert len(tickets) == 3


# ---------------------------------------------------------------------------
# Knowledge Base CRUD tests
# ---------------------------------------------------------------------------

class TestKnowledgeBaseCRUD:

    def test_create_kb_entry(self, db):
        entry = crud.create_kb_entry(
            db,
            topic="test_topic",
            keywords="test, keyword, example",
            content="This is test content.",
            category="test",
        )
        assert entry.id is not None
        assert entry.topic == "test_topic"

    def test_get_kb_entry_by_topic(self, db):
        crud.create_kb_entry(db, "findme", "find, search", "Findable content.")
        found = crud.get_kb_entry_by_topic(db, "findme")
        assert found is not None
        assert found.content == "Findable content."

    def test_search_kb_entries_matches(self, db):
        crud.create_kb_entry(db, "password_reset", "password, reset, forgot", "Reset your password here.")
        results = crud.search_kb_entries(db, "forgot my password", max_results=3)
        assert len(results) > 0
        assert results[0]["topic"] == "password_reset"

    def test_search_kb_no_match(self, db):
        results = crud.search_kb_entries(db, "xyzzy frobnicate ultrafoo")
        assert len(results) == 0

    def test_seed_knowledge_base(self, db):
        from backend.services.knowledge_service import seed_knowledge_base
        count = seed_knowledge_base(db)
        assert count > 0
        total = crud.count_kb_entries(db)
        assert total == count

    def test_seed_is_idempotent(self, db):
        from backend.services.knowledge_service import seed_knowledge_base
        count1 = seed_knowledge_base(db)
        count2 = seed_knowledge_base(db)
        assert count2 == 0  # second seed inserts nothing new
        assert crud.count_kb_entries(db) == count1


# ---------------------------------------------------------------------------
# Agent Metrics tests
# ---------------------------------------------------------------------------

class TestAgentMetrics:

    def test_create_metric(self, db):
        metric = crud.create_metric(
            db,
            channel="email",
            intent="billing",
            escalated=False,
            kb_used=True,
            kb_topic="billing_invoice",
            processing_time_ms=42.5,
        )
        assert metric.id is not None
        assert metric.channel == "email"
        assert metric.kb_used is True
        assert metric.processing_time_ms == 42.5

    def test_escalation_metric(self, db):
        metric = crud.create_metric(
            db,
            channel="whatsapp",
            intent="refund",
            escalated=True,
            escalation_reason="refund_request",
            kb_used=False,
        )
        assert metric.escalated is True
        assert metric.escalation_reason == "refund_request"
