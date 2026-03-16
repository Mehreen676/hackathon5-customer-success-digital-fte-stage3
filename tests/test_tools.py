"""
MCP Tool Tests — Customer Success Digital FTE (Stage 2)

Tests each MCP tool individually with an isolated in-memory database.
Tools tested: search_kb, create_ticket, get_customer_context,
              escalate_issue, send_channel_response.

Run with:
    pytest tests/test_tools.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.database import Base
from backend.database import crud, models  # noqa: F401
from backend.mcp.tool_registry import call_tool, init_tools, list_tools, is_registered


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def register_tools():
    """Register all MCP tools before any test in this module."""
    init_tools()


@pytest.fixture(scope="function")
def db():
    """Fresh in-memory SQLite DB with seeded KB and one sample customer."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed KB and sample customer
    from backend.services.knowledge_service import seed_all
    seed_all(session)

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# Tool Registry tests
# ---------------------------------------------------------------------------

class TestToolRegistry:

    def test_all_expected_tools_registered(self):
        expected = {
            "search_kb",
            "create_ticket",
            "get_customer_context",
            "escalate_issue",
            "send_channel_response",
        }
        registered = set(list_tools())
        assert expected.issubset(registered)

    def test_is_registered_true(self):
        assert is_registered("search_kb") is True

    def test_is_registered_false(self):
        assert is_registered("nonexistent_tool_xyz") is False

    def test_call_unknown_tool_raises(self, db):
        with pytest.raises(ValueError, match="not found in registry"):
            call_tool("nonexistent_tool_xyz", db=db)


# ---------------------------------------------------------------------------
# Tool: search_kb
# ---------------------------------------------------------------------------

class TestSearchKBTool:

    def test_password_query_matches(self, db):
        result = call_tool("search_kb", query="how do I reset my password?", db=db)
        assert result["matched"] is True
        assert any(r["topic"] == "password_reset" for r in result["results"])

    def test_billing_query_matches(self, db):
        result = call_tool("search_kb", query="I need my invoice", db=db)
        assert result["matched"] is True
        assert result["results"][0]["topic"] == "billing_invoice"

    def test_slack_query_matches(self, db):
        result = call_tool("search_kb", query="connect Slack workspace", db=db)
        assert result["matched"] is True

    def test_unknown_query_no_match(self, db):
        result = call_tool("search_kb", query="xyzzy frobnicate ultrafoo", db=db)
        assert result["matched"] is False

    def test_max_results_respected(self, db):
        result = call_tool("search_kb", query="password invoice slack", db=db, max_results=2)
        assert len(result["results"]) <= 2

    def test_result_contains_content(self, db):
        result = call_tool("search_kb", query="upgrade plan pricing", db=db)
        assert result["matched"] is True
        assert "content" in result["results"][0]
        assert len(result["results"][0]["content"]) > 0

    def test_result_has_source_field(self, db):
        result = call_tool("search_kb", query="password reset", db=db)
        assert "source" in result

    def test_fallback_works_with_empty_db(self):
        """search_kb should fall back to Stage 1 KB if the database is empty."""
        empty_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(empty_engine)
        EmptySession = sessionmaker(bind=empty_engine)
        empty_db = EmptySession()
        try:
            result = call_tool("search_kb", query="reset my password", db=empty_db)
            assert result["matched"] is True
            assert result["source"] == "fallback"
        finally:
            empty_db.close()
            Base.metadata.drop_all(empty_engine)


# ---------------------------------------------------------------------------
# Tool: create_ticket
# ---------------------------------------------------------------------------

class TestCreateTicketTool:

    def _get_customer_id(self, db):
        return crud.get_customer_by_external_id(db, "CUST-001").id

    def test_creates_ticket_with_ref(self, db):
        customer_id = self._get_customer_id(db)
        result = call_tool(
            "create_ticket",
            customer_id=customer_id,
            channel="email",
            subject="Test ticket",
            description="Test description",
            db=db,
        )
        assert result["ticket_ref"].startswith("TKT-")

    def test_ticket_has_correct_channel(self, db):
        customer_id = self._get_customer_id(db)
        result = call_tool(
            "create_ticket",
            customer_id=customer_id,
            channel="whatsapp",
            subject="WA ticket",
            description="WA description",
            db=db,
        )
        assert result["channel"] == "whatsapp"

    def test_escalated_ticket(self, db):
        customer_id = self._get_customer_id(db)
        result = call_tool(
            "create_ticket",
            customer_id=customer_id,
            channel="email",
            subject="Escalated",
            description="Legal threat",
            priority="high",
            status="escalated",
            escalated=True,
            escalation_reason="legal_complaint",
            db=db,
        )
        assert result["escalated"] is True
        assert result["status"] == "escalated"
        assert result["priority"] == "high"

    def test_two_tickets_have_unique_refs(self, db):
        customer_id = self._get_customer_id(db)
        t1 = call_tool("create_ticket", customer_id=customer_id, channel="email",
                       subject="T1", description="D1", db=db)
        t2 = call_tool("create_ticket", customer_id=customer_id, channel="email",
                       subject="T2", description="D2", db=db)
        assert t1["ticket_ref"] != t2["ticket_ref"]


# ---------------------------------------------------------------------------
# Tool: get_customer_context
# ---------------------------------------------------------------------------

class TestGetCustomerContextTool:

    def test_known_customer_found(self, db):
        customer = crud.get_customer_by_external_id(db, "CUST-001")
        result = call_tool("get_customer_context", customer_id=customer.id, db=db)
        assert result["found"] is True
        assert result["name"] == "Sarah Mitchell"

    def test_unknown_customer_returns_guest(self, db):
        result = call_tool("get_customer_context", customer_id="CUST-UNKNOWN", db=db)
        assert result["found"] is False
        assert result["name"] == "Valued Customer"
        assert result["is_vip"] is False

    def test_vip_customer_is_flagged(self, db):
        customer = crud.get_customer_by_external_id(db, "CUST-005")
        result = call_tool("get_customer_context", customer_id=customer.id, db=db)
        assert result["found"] is True
        assert result["is_vip"] is True
        assert result["account_tier"] == "enterprise"

    def test_context_includes_ticket_count(self, db):
        customer = crud.get_customer_by_external_id(db, "CUST-001")
        result = call_tool("get_customer_context", customer_id=customer.id, db=db)
        assert "ticket_count" in result
        assert "recent_tickets" in result


# ---------------------------------------------------------------------------
# Tool: escalate_issue
# ---------------------------------------------------------------------------

class TestEscalateIssueTool:

    def _create_test_ticket(self, db):
        customer = crud.get_customer_by_external_id(db, "CUST-001")
        return crud.create_ticket(
            db,
            customer_id=customer.id,
            channel="email",
            subject="Test escalation",
            description="Needs escalation",
            priority="high",
        )

    def test_escalation_returns_holding_response(self, db):
        ticket = self._create_test_ticket(db)
        result = call_tool(
            "escalate_issue",
            ticket_id=ticket.id,
            ticket_ref=ticket.ticket_ref,
            reason="refund_request",
            severity="medium",
            channel="email",
            customer_name="Sarah Mitchell",
            db=db,
        )
        assert result["escalated"] is True
        assert "holding_response" in result
        assert len(result["holding_response"]) > 0

    def test_ticket_ref_appears_in_response(self, db):
        ticket = self._create_test_ticket(db)
        result = call_tool(
            "escalate_issue",
            ticket_id=ticket.id,
            ticket_ref=ticket.ticket_ref,
            reason="legal_complaint",
            severity="high",
            channel="email",
            customer_name="Daniel Cruz",
            db=db,
        )
        assert ticket.ticket_ref in result["holding_response"]

    def test_correct_team_assigned_for_refund(self, db):
        ticket = self._create_test_ticket(db)
        result = call_tool(
            "escalate_issue",
            ticket_id=ticket.id,
            ticket_ref=ticket.ticket_ref,
            reason="refund_request",
            severity="medium",
            channel="web_form",
            customer_name="Priya Sharma",
            db=db,
        )
        assert result["assigned_team"] == "Billing"

    def test_critical_severity_has_fast_sla(self, db):
        ticket = self._create_test_ticket(db)
        result = call_tool(
            "escalate_issue",
            ticket_id=ticket.id,
            ticket_ref=ticket.ticket_ref,
            reason="security_issue",
            severity="critical",
            channel="whatsapp",
            customer_name="Amara Diallo",
            db=db,
        )
        assert result["sla"] == "2 hours"

    def test_whatsapp_escalation_is_concise(self, db):
        ticket = self._create_test_ticket(db)
        result = call_tool(
            "escalate_issue",
            ticket_id=ticket.id,
            ticket_ref=ticket.ticket_ref,
            reason="angry_customer",
            severity="medium",
            channel="whatsapp",
            customer_name="James Okafor",
            db=db,
        )
        word_count = len(result["holding_response"].split())
        assert word_count <= 80, f"WhatsApp escalation too long: {word_count} words"


# ---------------------------------------------------------------------------
# Tool: send_channel_response
# ---------------------------------------------------------------------------

class TestSendChannelResponseTool:

    TEST_BODY = "To reset your password go to nexora.io/login and click Forgot Password."

    def test_email_has_dear_salutation(self):
        result = call_tool(
            "send_channel_response",
            message_body=self.TEST_BODY,
            channel="email",
            customer_name="Sarah Mitchell",
            ticket_ref="TKT-TESTREF",
        )
        assert "Dear Sarah" in result["response"]

    def test_email_has_sign_off(self):
        result = call_tool(
            "send_channel_response",
            message_body=self.TEST_BODY,
            channel="email",
            customer_name="Sarah Mitchell",
        )
        assert "Best regards" in result["response"]
        assert "Nexora Customer Success Team" in result["response"]

    def test_whatsapp_starts_with_hi(self):
        result = call_tool(
            "send_channel_response",
            message_body=self.TEST_BODY,
            channel="whatsapp",
            customer_name="James Okafor",
        )
        assert "Hi James" in result["response"]

    def test_whatsapp_is_concise(self):
        result = call_tool(
            "send_channel_response",
            message_body=self.TEST_BODY,
            channel="whatsapp",
            customer_name="James Okafor",
        )
        assert len(result["response"].split()) <= 100

    def test_webform_acknowledges_submission(self):
        result = call_tool(
            "send_channel_response",
            message_body=self.TEST_BODY,
            channel="web_form",
            customer_name="Priya Sharma",
            ticket_ref="TKT-WEB001",
        )
        assert "Thanks for reaching out" in result["response"]

    def test_ticket_ref_included_in_email(self):
        result = call_tool(
            "send_channel_response",
            message_body=self.TEST_BODY,
            channel="email",
            customer_name="Daniel Cruz",
            ticket_ref="TKT-REF123",
        )
        assert "TKT-REF123" in result["response"]

    def test_channel_field_correct(self):
        result = call_tool(
            "send_channel_response",
            message_body=self.TEST_BODY,
            channel="whatsapp",
            customer_name="Test User",
        )
        assert result["channel"] == "whatsapp"

    def test_email_and_whatsapp_differ(self):
        email_result = call_tool(
            "send_channel_response",
            message_body=self.TEST_BODY,
            channel="email",
            customer_name="Test User",
        )
        wa_result = call_tool(
            "send_channel_response",
            message_body=self.TEST_BODY,
            channel="whatsapp",
            customer_name="Test User",
        )
        assert email_result["response"] != wa_result["response"]
