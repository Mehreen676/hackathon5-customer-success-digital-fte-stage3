"""
Agent Workflow Tests — Customer Success Digital FTE (Stage 2)

Tests the Stage 2 agent workflow end-to-end using an isolated in-memory
database. Verifies the full processing pipeline including customer lookup,
escalation detection, KB search, ticket creation, and response formatting.

Run with:
    pytest tests/test_workflow.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.database import Base
from backend.database import crud, models  # noqa: F401
from backend.mcp.tool_registry import init_tools
from backend.agents.workflow import process_message
from backend.agents.escalation_engine import detect_escalation, classify_intent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def register_tools():
    init_tools()


@pytest.fixture(scope="function")
def db():
    """Fresh in-memory SQLite DB with seeded data for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    from backend.services.knowledge_service import seed_all
    seed_all(session)

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# Escalation Engine unit tests
# ---------------------------------------------------------------------------

class TestEscalationEngine:

    def _guest(self):
        return {"is_vip": False, "account_tier": "growth"}

    def _vip(self):
        return {"is_vip": True, "account_tier": "enterprise"}

    def test_refund_triggers_escalation(self):
        result = detect_escalation("I need a full refund immediately", self._guest())
        assert result is not None
        assert result["reason"] == "refund_request"
        assert result["severity"] == "medium"

    def test_legal_triggers_high_severity(self):
        result = detect_escalation("I will consult my attorney about legal action", self._guest())
        assert result is not None
        assert result["reason"] == "legal_complaint"
        assert result["severity"] == "high"

    def test_security_triggers_critical(self):
        result = detect_escalation("My account was hacked", self._guest())
        assert result is not None
        assert result["reason"] == "security_issue"
        assert result["severity"] == "critical"

    def test_angry_customer_triggers(self):
        result = detect_escalation("This is completely unacceptable", self._guest())
        assert result is not None
        assert result["reason"] == "angry_customer"

    def test_pricing_negotiation_triggers(self):
        result = detect_escalation("Can you match the competitor price or give a discount?", self._guest())
        assert result is not None
        assert result["reason"] == "pricing_negotiation"

    def test_vip_with_complaint_triggers(self):
        result = detect_escalation("The integration is broken and not working", self._vip())
        assert result is not None
        assert result["reason"] == "vip_complaint"
        assert result["severity"] == "high"

    def test_routine_message_no_escalation(self):
        result = detect_escalation("How do I reset my password?", self._guest())
        assert result is None

    def test_invoice_question_no_escalation(self):
        result = detect_escalation("Where can I find my invoice?", self._guest())
        assert result is None

    def test_case_insensitive_detection(self):
        result = detect_escalation("I WANT MY MONEY BACK NOW", self._guest())
        assert result is not None
        assert result["reason"] == "refund_request"

    def test_vip_routine_question_no_escalation(self):
        result = detect_escalation("How do I invite a team member?", self._vip())
        assert result is None


class TestIntentClassification:

    def test_billing_intent(self):
        assert classify_intent("Where is my invoice?") == "billing"

    def test_account_intent(self):
        assert classify_intent("I am locked out of my account") == "account"

    def test_integration_intent(self):
        assert classify_intent("How do I connect Slack?") == "integration"

    def test_plan_intent(self):
        assert classify_intent("I want to upgrade my plan") == "plan"

    def test_team_intent(self):
        assert classify_intent("How do I invite a team member?") == "team"

    def test_cancellation_intent(self):
        assert classify_intent("I want to cancel my subscription") == "cancellation"

    def test_general_intent_fallback(self):
        assert classify_intent("Good morning, how are you?") == "general"


# ---------------------------------------------------------------------------
# Full workflow pipeline tests
# ---------------------------------------------------------------------------

class TestWorkflowPipeline:

    def test_routine_email_not_escalated(self, db):
        result = process_message("CUST-001", "email", "How do I reset my password?", db)
        assert result["success"] is True
        assert result["escalated"] is False
        assert result["kb_used"] is True

    def test_refund_request_escalated(self, db):
        result = process_message("CUST-002", "web_form", "I want a full refund please", db)
        assert result["success"] is True
        assert result["escalated"] is True
        assert result["escalation_reason"] == "refund_request"

    def test_legal_threat_escalated(self, db):
        result = process_message(
            "CUST-001", "email",
            "If this is not resolved I will consult my attorney about legal action",
            db
        )
        assert result["success"] is True
        assert result["escalated"] is True
        assert result["escalation_reason"] == "legal_complaint"
        assert result["escalation_severity"] == "high"

    def test_security_issue_critical(self, db):
        result = process_message(
            "CUST-003", "email",
            "My account was hacked and someone logged in",
            db
        )
        assert result["escalated"] is True
        assert result["escalation_reason"] == "security_issue"

    def test_vip_enterprise_complaint_escalated(self, db):
        result = process_message(
            "CUST-005", "whatsapp",
            "The SSO integration is broken and not working for days",
            db
        )
        assert result["escalated"] is True
        assert result["escalation_reason"] == "vip_complaint"

    def test_kb_search_used_when_no_escalation(self, db):
        result = process_message("CUST-001", "email", "How do I add a team member?", db)
        assert result["escalated"] is False
        assert result["kb_used"] is True
        assert result["kb_topic"] == "add_team_member"

    def test_unknown_query_no_kb_match(self, db):
        result = process_message(
            "CUST-002", "email",
            "Tell me about your advanced API rate limiting documentation",
            db
        )
        assert result["escalated"] is False
        assert result["kb_used"] is False

    def test_ticket_always_created(self, db):
        result = process_message("CUST-001", "whatsapp", "Hello, need some help", db)
        assert "ticket" in result
        assert result["ticket"]["ticket_ref"].startswith("TKT-")

    def test_conversation_id_returned(self, db):
        result = process_message("CUST-003", "email", "Where is my invoice?", db)
        assert "conversation_id" in result
        assert result["conversation_id"] is not None

    def test_invalid_channel_returns_error(self, db):
        result = process_message("CUST-001", "fax", "Hello", db)
        assert result["success"] is False
        assert "error" in result

    def test_all_channels_return_response(self, db):
        for channel in ["email", "whatsapp", "web_form"]:
            result = process_message("CUST-001", channel, "How do I upgrade my plan?", db)
            assert result["success"] is True
            assert len(result["response"]) > 0

    def test_unknown_customer_auto_created(self, db):
        result = process_message(
            "CUST-NEW-999", "email",
            "Hello, I am a new customer with a question",
            db
        )
        assert result["success"] is True
        # Customer should be created in the database
        customer = crud.get_customer_by_external_id(db, "CUST-NEW-999")
        assert customer is not None

    def test_conversation_history_stored(self, db):
        result = process_message("CUST-001", "email", "How do I reset my password?", db)
        conversation_id = result["conversation_id"]
        messages = crud.get_conversation_messages(db, conversation_id)
        # Should have customer message + agent response
        assert len(messages) == 2
        assert messages[0].role == "customer"
        assert messages[1].role == "agent"

    def test_email_response_is_formal(self, db):
        result = process_message("CUST-001", "email", "How do I reset my password?", db)
        assert "Dear" in result["response"] or "Thank you for contacting" in result["response"]

    def test_whatsapp_response_is_concise(self, db):
        result = process_message("CUST-002", "whatsapp", "I need my invoice", db)
        word_count = len(result["response"].split())
        assert word_count <= 150, f"WhatsApp response too long: {word_count} words"

    def test_same_customer_gets_same_conversation(self, db):
        """Two messages from the same customer on the same channel should reuse the conversation."""
        r1 = process_message("CUST-001", "email", "First message", db)
        r2 = process_message("CUST-001", "email", "Second message", db)
        assert r1["conversation_id"] == r2["conversation_id"]

    def test_different_channels_get_different_conversations(self, db):
        """Same customer on different channels gets different conversations."""
        r1 = process_message("CUST-001", "email", "Email message", db)
        r2 = process_message("CUST-001", "whatsapp", "WhatsApp message", db)
        assert r1["conversation_id"] != r2["conversation_id"]
