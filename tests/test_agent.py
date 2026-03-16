"""
Tests — Customer Success Digital FTE (Stage 1 Prototype)

Tests cover the four core behaviors:
    1. Escalation detection
    2. Knowledge base lookup
    3. Channel response formatting
    4. Ticket creation

Run with:
    pytest tests/test_agent.py -v

Note: Tests import directly from backend/agent_v1/ using sys.path manipulation
so no package installation is required.
"""

import sys
import os
import pytest

# Allow imports from backend/agent_v1/ without installing as a package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "agent_v1"))

from mcp_server import search_kb, create_ticket, get_history, send_response, escalate_to_human
from customer_success_agent import check_escalation, classify_intent, process_message


# ===========================================================================
# 1. ESCALATION DETECTION TESTS
# ===========================================================================

class TestEscalationDetection:

    def _guest_customer(self):
        return {"is_vip": False, "account_tier": "Growth"}

    def _vip_customer(self):
        return {"is_vip": True, "account_tier": "Enterprise"}

    def test_refund_keyword_triggers_escalation(self):
        result = check_escalation("I need a refund for my payment", self._guest_customer())
        assert result is not None
        assert result["reason"] == "refund_request"
        assert result["severity"] == "medium"

    def test_legal_keyword_triggers_high_severity(self):
        result = check_escalation("I am consulting my attorney about legal action", self._guest_customer())
        assert result is not None
        assert result["reason"] == "legal_complaint"
        assert result["severity"] == "high"

    def test_angry_customer_keyword_triggers_escalation(self):
        result = check_escalation("This is completely unacceptable service", self._guest_customer())
        assert result is not None
        assert result["reason"] == "angry_customer"

    def test_pricing_negotiation_triggers_escalation(self):
        result = check_escalation("Can you match your competitor price?", self._guest_customer())
        assert result is not None
        assert result["reason"] == "pricing_negotiation"

    def test_security_issue_triggers_critical_severity(self):
        result = check_escalation("My account was hacked, someone logged in", self._guest_customer())
        assert result is not None
        assert result["reason"] == "security_issue"
        assert result["severity"] == "critical"

    def test_routine_message_does_not_escalate(self):
        result = check_escalation("How do I reset my password?", self._guest_customer())
        assert result is None

    def test_invoice_question_does_not_escalate(self):
        result = check_escalation("Where can I find my invoice?", self._guest_customer())
        assert result is None

    def test_vip_with_complaint_escalates(self):
        result = check_escalation("The integration is not working for us", self._vip_customer())
        assert result is not None
        assert result["reason"] == "vip_complaint"
        assert result["severity"] == "high"

    def test_vip_with_routine_question_does_not_escalate(self):
        # VIP asking a plain question — no complaint signal
        result = check_escalation("How do I invite a new team member?", self._vip_customer())
        assert result is None

    def test_case_insensitive_detection(self):
        result = check_escalation("I WANT MY MONEY BACK IMMEDIATELY", self._guest_customer())
        assert result is not None
        assert result["reason"] == "refund_request"


# ===========================================================================
# 2. KNOWLEDGE BASE LOOKUP TESTS
# ===========================================================================

class TestKnowledgeBaseSearch:

    def test_password_query_matches_kb(self):
        result = search_kb("how do I reset my password?")
        assert result["matched"] is True
        assert len(result["results"]) > 0
        top = result["results"][0]
        assert top["topic"] == "password_reset"

    def test_invoice_query_matches_kb(self):
        result = search_kb("where can I find my invoice")
        assert result["matched"] is True
        assert result["results"][0]["topic"] == "billing_invoice"

    def test_slack_query_matches_kb(self):
        result = search_kb("how do I connect Slack?")
        assert result["matched"] is True
        assert result["results"][0]["topic"] == "slack_integration"

    def test_unknown_query_returns_no_match(self):
        result = search_kb("xyzzy frobnicate ultrafoo")
        assert result["matched"] is False
        assert result["results"] == []

    def test_upgrade_plan_query_matches(self):
        result = search_kb("I want to upgrade my plan to Business")
        assert result["matched"] is True
        assert any(r["topic"] == "plan_upgrade" for r in result["results"])

    def test_max_results_respected(self):
        # Even a broad query should respect max_results
        result = search_kb("password invoice slack plan", max_results=2)
        assert len(result["results"]) <= 2

    def test_result_contains_content(self):
        result = search_kb("reset password")
        assert result["matched"] is True
        assert "content" in result["results"][0]
        assert len(result["results"][0]["content"]) > 0


# ===========================================================================
# 3. CHANNEL FORMATTING TESTS
# ===========================================================================

class TestChannelFormatting:

    TEST_BODY = "To reset your password, go to nexora.io/login and click Forgot Password."

    def test_email_response_has_salutation(self):
        result = send_response(self.TEST_BODY, "email", "Sarah Mitchell", "TKT-001")
        assert "Dear Sarah" in result["response"]

    def test_email_response_has_sign_off(self):
        result = send_response(self.TEST_BODY, "email", "Sarah Mitchell", "TKT-001")
        assert "Best regards" in result["response"]
        assert "Nexora Customer Success Team" in result["response"]

    def test_whatsapp_response_is_short(self):
        result = send_response(self.TEST_BODY, "whatsapp", "James Okafor")
        word_count = len(result["response"].split())
        assert word_count <= 100, f"WhatsApp response too long: {word_count} words"

    def test_whatsapp_response_has_friendly_opener(self):
        result = send_response(self.TEST_BODY, "whatsapp", "James Okafor")
        assert "Hi James" in result["response"]

    def test_web_form_response_acknowledges_submission(self):
        result = send_response(self.TEST_BODY, "web_form", "Priya Sharma", "TKT-002")
        assert "Thanks for reaching out" in result["response"]

    def test_web_form_includes_ticket_reference(self):
        result = send_response(self.TEST_BODY, "web_form", "Priya Sharma", "TKT-002")
        assert "TKT-002" in result["response"]

    def test_email_and_whatsapp_responses_are_different(self):
        email_result = send_response(self.TEST_BODY, "email", "Sarah Mitchell")
        whatsapp_result = send_response(self.TEST_BODY, "whatsapp", "Sarah Mitchell")
        assert email_result["response"] != whatsapp_result["response"]

    def test_channel_field_returned_correctly(self):
        result = send_response(self.TEST_BODY, "email", "Sarah Mitchell")
        assert result["channel"] == "email"

    def test_first_name_extraction_from_full_name(self):
        result = send_response(self.TEST_BODY, "whatsapp", "Daniel Cruz")
        assert "Hi Daniel" in result["response"]


# ===========================================================================
# 4. TICKET CREATION TESTS
# ===========================================================================

class TestTicketCreation:

    def test_ticket_has_unique_id(self):
        t1 = create_ticket("CUST-001", "email", "Test", "msg", "low")
        t2 = create_ticket("CUST-001", "email", "Test", "msg", "low")
        assert t1["ticket_id"] != t2["ticket_id"]

    def test_ticket_id_format(self):
        ticket = create_ticket("CUST-002", "whatsapp", "Invoice help", "Where is invoice?", "low")
        assert ticket["ticket_id"].startswith("TKT-")

    def test_ticket_status_is_set(self):
        ticket = create_ticket("CUST-003", "web_form", "Refund", "I want a refund", "medium", "escalated")
        assert ticket["status"] == "escalated"

    def test_ticket_priority_is_set(self):
        ticket = create_ticket("CUST-001", "email", "Legal", "Legal threat", "high")
        assert ticket["priority"] == "high"

    def test_ticket_has_created_at(self):
        ticket = create_ticket("CUST-001", "email", "Test", "test message")
        assert "created_at" in ticket
        assert ticket["created_at"].endswith("Z")


# ===========================================================================
# 5. FULL PIPELINE INTEGRATION TESTS
# ===========================================================================

class TestFullPipeline:

    def test_routine_message_not_escalated(self):
        result = process_message("CUST-001", "email", "How do I reset my password?")
        assert result["success"] is True
        assert result["escalated"] is False
        assert result["kb_used"] is True

    def test_refund_message_is_escalated(self):
        result = process_message("CUST-003", "web_form", "I want a full refund please")
        assert result["success"] is True
        assert result["escalated"] is True
        assert result["escalation_reason"] == "refund_request"

    def test_response_is_returned_for_all_channels(self):
        for channel in ["email", "whatsapp", "web_form"]:
            result = process_message("CUST-001", channel, "How do I add a team member?")
            assert result["success"] is True
            assert len(result["response"]) > 0

    def test_ticket_always_created(self):
        result = process_message("CUST-002", "whatsapp", "Hello, need some help")
        assert "ticket" in result
        assert result["ticket"]["ticket_id"].startswith("TKT-")

    def test_invalid_channel_returns_error(self):
        result = process_message("CUST-001", "fax", "Hello")
        assert result["success"] is False
        assert "error" in result
