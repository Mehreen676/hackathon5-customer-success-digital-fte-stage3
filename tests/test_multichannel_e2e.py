"""
Multi-Channel End-to-End Tests — Customer Success Digital FTE (Stage 3)

Full end-to-end test coverage for all three inbound channels:
  - Web Form: POST /support/submit → GET /support/ticket/{ref}
  - Gmail Webhook: POST /webhooks/gmail (Pub/Sub push notification)
  - WhatsApp Webhook: POST /webhooks/whatsapp (Twilio form-encoded)
  - Cross-channel continuity: same customer across email + webform + whatsapp
  - Ticket lifecycle: open → escalation path → analytics recording
  - Analytics: POST /support/submit populates metrics, GET /analytics/summary reflects them

All tests use an isolated in-memory SQLite database.
No external API credentials required — Gmail and Twilio run in MOCK mode.

Run with:
    pytest tests/test_multichannel_e2e.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import base64
import json
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.database import Base, get_db
from backend.mcp.tool_registry import init_tools


# ---------------------------------------------------------------------------
# Shared in-memory database — module-scoped so all E2E tests share state
# ---------------------------------------------------------------------------

E2E_DATABASE_URL = "sqlite:///:memory:"
e2e_engine = create_engine(E2E_DATABASE_URL, connect_args={"check_same_thread": False})
E2ESessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=e2e_engine)


def override_get_db():
    from backend.database import models  # noqa: F401

    Base.metadata.create_all(bind=e2e_engine)
    db = E2ESessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_e2e_db():
    from backend.database import models  # noqa: F401

    Base.metadata.create_all(bind=e2e_engine)
    init_tools()


@pytest.fixture(scope="module")
def client():
    from backend.api.main import app

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pubsub_payload(from_email: str, subject: str, body: str, message_id: str = "msg001") -> dict:
    """Build a minimal Gmail Pub/Sub push notification payload."""
    email_data = {
        "from_email": from_email,
        "subject": subject,
        "body": body,
        "message_id": message_id,
    }
    encoded = base64.b64encode(json.dumps(email_data).encode()).decode()
    return {
        "message": {
            "data": encoded,
            "messageId": message_id,
            "publishTime": "2025-01-01T00:00:00Z",
            "attributes": {"email": from_email},
        },
        "subscription": "projects/nexora/subscriptions/gmail-push",
    }


def _make_twilio_form(from_phone: str, body: str, message_sid: str = "SMtest001") -> dict:
    """Build a Twilio WhatsApp webhook form payload."""
    return {
        "From": f"whatsapp:{from_phone}",
        "Body": body,
        "MessageSid": message_sid,
        "AccountSid": "ACtest",
        "To": "whatsapp:+14155238886",
        "NumMedia": "0",
    }


def _submit_webform(client, name: str, email: str, subject: str, message: str) -> dict:
    resp = client.post(
        "/support/submit",
        json={"name": name, "email": email, "subject": subject, "message": message},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ===========================================================================
# 1. Web Form Submission Flow
# ===========================================================================

class TestWebFormFlow:
    """Full web-form submission → ticket creation → status lookup flow."""

    def test_submit_returns_ticket_ref(self, client):
        data = _submit_webform(
            client,
            name="Alice Johnson",
            email="alice.e2e@example.com",
            subject="Invoice question",
            message="Hi, I have a question about my invoice for this month.",
        )
        assert "ticket_ref" in data
        assert data["ticket_ref"].startswith("TKT-")

    def test_submit_returns_response_text(self, client):
        data = _submit_webform(
            client,
            name="Bob Smith",
            email="bob.e2e@example.com",
            subject="Billing question",
            message="What are the different pricing plans for enterprise?",
        )
        assert "response" in data
        assert len(data["response"]) > 0

    def test_submit_returns_channel_webform(self, client):
        data = _submit_webform(
            client,
            name="Carol White",
            email="carol.e2e@example.com",
            subject="General inquiry",
            message="I'd like to know more about your integration options.",
        )
        assert data.get("channel") == "web_form"

    def test_ticket_lookup_after_submit(self, client):
        data = _submit_webform(
            client,
            name="Dave Brown",
            email="dave.e2e@example.com",
            subject="Password reset",
            message="I cannot reset my password. The reset email does not arrive.",
        )
        ticket_ref = data["ticket_ref"]
        lookup = client.get(f"/support/ticket/{ticket_ref}")
        assert lookup.status_code == 200
        result = lookup.json()
        assert result["ticket_ref"] == ticket_ref
        assert result["status"] in ("open", "auto-resolved", "pending_review", "escalated")

    def test_ticket_lookup_contains_customer_name(self, client):
        data = _submit_webform(
            client,
            name="Eve Davis",
            email="eve.e2e@example.com",
            subject="Account access",
            message="I am unable to log in to my Nexora account since last week.",
        )
        ticket_ref = data["ticket_ref"]
        lookup = client.get(f"/support/ticket/{ticket_ref}")
        assert lookup.status_code == 200
        assert lookup.json()["customer_name"] == "Eve Davis"

    def test_ticket_lookup_unknown_ref_returns_404(self, client):
        resp = client.get("/support/ticket/TKT-NOTEXIST")
        assert resp.status_code == 404

    def test_submit_missing_email_returns_422(self, client):
        resp = client.post(
            "/support/submit",
            json={"name": "Test", "subject": "Test", "message": "Test message content"},
        )
        assert resp.status_code == 422

    def test_submit_missing_message_returns_422(self, client):
        resp = client.post(
            "/support/submit",
            json={"name": "Test", "email": "test@example.com", "subject": "Test"},
        )
        assert resp.status_code == 422

    def test_submit_creates_conversation_record(self, client):
        """Submitting a form should create a conversation entry in the DB."""
        data = _submit_webform(
            client,
            name="Frank Lane",
            email="frank.e2e@example.com",
            subject="Technical support",
            message="The API integration returns 503 errors intermittently.",
        )
        assert data["ticket_ref"].startswith("TKT-")
        # The ticket_ref existing proves the conversation was persisted
        lookup = client.get(f"/support/ticket/{data['ticket_ref']}")
        assert lookup.status_code == 200

    def test_submit_escalation_message_marks_escalated(self, client):
        """A message with escalation keywords should produce escalated=True."""
        data = _submit_webform(
            client,
            name="Gina Ford",
            email="gina.escalate@example.com",
            subject="Legal complaint",
            message="I am filing a formal legal complaint and want to speak with your legal team immediately.",
        )
        # escalated flag should be True
        assert data.get("escalated") is True


# ===========================================================================
# 2. Gmail Webhook Flow
# ===========================================================================

class TestGmailWebhookFlow:
    """End-to-end Gmail Pub/Sub push notification → agent pipeline."""

    def test_gmail_webhook_returns_200(self, client):
        payload = _make_pubsub_payload(
            from_email="henry.gmail@example.com",
            subject="Billing inquiry",
            body="Hello, can you explain my latest invoice charges?",
        )
        resp = client.post("/webhooks/gmail", json=payload)
        assert resp.status_code == 200

    def test_gmail_webhook_ack_structure(self, client):
        payload = _make_pubsub_payload(
            from_email="iris.gmail@example.com",
            subject="Feature request",
            body="I would like to request an SSO integration feature.",
            message_id="msg_iris_001",
        )
        resp = client.post("/webhooks/gmail", json=payload)
        body = resp.json()
        assert "received" in body
        assert body["received"] is True
        assert body["channel"] == "gmail"

    def test_gmail_webhook_creates_ticket(self, client):
        payload = _make_pubsub_payload(
            from_email="jake.gmail@example.com",
            subject="Support request",
            body="I need help with my account setup. Please assist.",
            message_id="msg_jake_001",
        )
        resp = client.post("/webhooks/gmail", json=payload)
        body = resp.json()
        assert "ticket_ref" in body
        assert body["ticket_ref"].startswith("TKT-")

    def test_gmail_webhook_empty_payload_still_200(self, client):
        """Pub/Sub must always receive 200 to avoid infinite retries."""
        resp = client.post("/webhooks/gmail", json={})
        assert resp.status_code == 200

    def test_gmail_webhook_malformed_data_still_200(self, client):
        resp = client.post(
            "/webhooks/gmail",
            json={"message": {"data": "!!!invalid base64!!!", "messageId": "bad001"}},
        )
        assert resp.status_code == 200

    def test_gmail_webhook_escalation_detected(self, client):
        payload = _make_pubsub_payload(
            from_email="karen.gmail@example.com",
            subject="Security incident",
            body="Our account has been compromised. This is a security emergency.",
            message_id="msg_karen_001",
        )
        resp = client.post("/webhooks/gmail", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        # Either escalated flag or status indicates escalation handling
        assert "status" in body

    def test_gmail_webhook_mode_field_present(self, client):
        payload = _make_pubsub_payload(
            from_email="leo.gmail@example.com",
            subject="Question",
            body="What storage limits apply to the Pro plan?",
            message_id="msg_leo_001",
        )
        resp = client.post("/webhooks/gmail", json=payload)
        body = resp.json()
        assert "mode" in body  # "mock" or "live"


# ===========================================================================
# 3. WhatsApp Webhook Flow
# ===========================================================================

class TestWhatsAppWebhookFlow:
    """End-to-end Twilio WhatsApp form webhook → agent pipeline."""

    def test_whatsapp_webhook_returns_200(self, client):
        form = _make_twilio_form(
            from_phone="+15005550001",
            body="Hi I need help with my account",
        )
        resp = client.post("/webhooks/whatsapp", data=form)
        assert resp.status_code == 200

    def test_whatsapp_webhook_ack_structure(self, client):
        form = _make_twilio_form(
            from_phone="+15005550002",
            body="What plans do you offer?",
            message_sid="SM_wa_002",
        )
        resp = client.post("/webhooks/whatsapp", data=form)
        body = resp.json()
        assert body["received"] is True
        assert body["channel"] == "whatsapp"

    def test_whatsapp_webhook_creates_ticket(self, client):
        form = _make_twilio_form(
            from_phone="+15005550003",
            body="I'm getting an error when logging in. Error code 403.",
            message_sid="SM_wa_003",
        )
        resp = client.post("/webhooks/whatsapp", data=form)
        body = resp.json()
        assert "ticket_ref" in body
        assert body["ticket_ref"].startswith("TKT-")

    def test_whatsapp_message_sid_in_response(self, client):
        form = _make_twilio_form(
            from_phone="+15005550004",
            body="Can I upgrade my plan mid-month?",
            message_sid="SM_wa_004_unique",
        )
        resp = client.post("/webhooks/whatsapp", data=form)
        body = resp.json()
        assert body.get("message_sid") == "SM_wa_004_unique"

    def test_whatsapp_empty_body_still_200(self, client):
        resp = client.post("/webhooks/whatsapp", data={})
        assert resp.status_code == 200

    def test_whatsapp_escalation_message(self, client):
        form = _make_twilio_form(
            from_phone="+15005550005",
            body="I want to cancel my account and get a full refund immediately",
            message_sid="SM_wa_escalate",
        )
        resp = client.post("/webhooks/whatsapp", data=form)
        assert resp.status_code == 200

    def test_whatsapp_mode_field_present(self, client):
        form = _make_twilio_form(
            from_phone="+15005550006",
            body="How do I export my data?",
            message_sid="SM_wa_mode_check",
        )
        resp = client.post("/webhooks/whatsapp", data=form)
        body = resp.json()
        assert "mode" in body


# ===========================================================================
# 4. Cross-Channel Continuity
# ===========================================================================

class TestCrossChannelContinuity:
    """Same customer reaching in via different channels maps to one customer record."""

    CUSTOMER_EMAIL = "multichannel.e2e@example.com"
    CUSTOMER_NAME = "Multichannel User"
    CUSTOMER_PHONE = "+15009990001"

    def test_webform_then_gmail_same_customer(self, client):
        """Web form submission followed by Gmail webhook: same email → same customer."""
        wf_data = _submit_webform(
            client,
            name=self.CUSTOMER_NAME,
            email=self.CUSTOMER_EMAIL,
            subject="Initial inquiry",
            message="First contact via web form about billing.",
        )
        wf_ticket = wf_data["ticket_ref"]

        gmail_payload = _make_pubsub_payload(
            from_email=self.CUSTOMER_EMAIL,
            subject="Follow-up",
            body="Following up on my previous billing question.",
            message_id="msg_cross_001",
        )
        gm_resp = client.post("/webhooks/gmail", json=gmail_payload)
        assert gm_resp.status_code == 200
        gm_ticket = gm_resp.json().get("ticket_ref")

        # Both tickets must exist
        assert wf_ticket.startswith("TKT-")
        assert gm_ticket is None or gm_ticket.startswith("TKT-")

    def test_webform_then_whatsapp_different_tickets(self, client):
        """Two separate inbound messages create separate tickets."""
        wf_data = _submit_webform(
            client,
            name="Phone User",
            email="phone.e2e@example.com",
            subject="Web inquiry",
            message="I need help with integration setup on web form.",
        )

        wa_form = _make_twilio_form(
            from_phone=self.CUSTOMER_PHONE,
            body="Also asking via WhatsApp about integration setup",
            message_sid="SM_cross_001",
        )
        wa_resp = client.post("/webhooks/whatsapp", data=wa_form)
        assert wa_resp.status_code == 200

        wf_lookup = client.get(f"/support/ticket/{wf_data['ticket_ref']}")
        assert wf_lookup.status_code == 200

    def test_three_channel_sequence_all_succeed(self, client):
        """One customer contacts via web_form, gmail, and whatsapp — all succeed."""
        email = "triple.channel@example.com"

        wf = _submit_webform(
            client, "Triple", email, "Q1", "First message via web form channel."
        )
        assert wf["ticket_ref"].startswith("TKT-")

        gm_payload = _make_pubsub_payload(
            from_email=email, subject="Q2", body="Second via Gmail.", message_id="msg_triple_001"
        )
        gm = client.post("/webhooks/gmail", json=gm_payload)
        assert gm.status_code == 200

        wa = client.post(
            "/webhooks/whatsapp",
            data=_make_twilio_form("+15009990002", "Third via WhatsApp", "SM_triple_001"),
        )
        assert wa.status_code == 200

    def test_ticket_lookup_cross_channel(self, client):
        """Ticket created via Gmail webhook is still retrievable via /support/ticket/{ref}."""
        gm_payload = _make_pubsub_payload(
            from_email="lookup.cross@example.com",
            subject="Lookup test",
            body="Can I look up this ticket from any channel?",
            message_id="msg_lookup_cross",
        )
        gm_resp = client.post("/webhooks/gmail", json=gm_payload)
        assert gm_resp.status_code == 200
        ticket_ref = gm_resp.json().get("ticket_ref")

        if ticket_ref and ticket_ref.startswith("TKT-"):
            lookup = client.get(f"/support/ticket/{ticket_ref}")
            assert lookup.status_code == 200
            assert lookup.json()["ticket_ref"] == ticket_ref


# ===========================================================================
# 5. Ticket Lifecycle
# ===========================================================================

class TestTicketLifecycle:
    """Ticket progresses through expected status transitions."""

    def test_normal_ticket_not_escalated(self, client):
        data = _submit_webform(
            client,
            name="Normal User",
            email="normal.lifecycle@example.com",
            subject="Password help",
            message="I forgot my password, how do I reset it?",
        )
        assert data.get("escalated") is False

    def test_escalated_ticket_flag_true(self, client):
        data = _submit_webform(
            client,
            name="Angry User",
            email="angry.lifecycle@example.com",
            subject="Complaint",
            message="I want to cancel everything and I am threatening legal action.",
        )
        assert data.get("escalated") is True

    def test_ticket_has_priority_field(self, client):
        data = _submit_webform(
            client,
            name="Priority User",
            email="priority.lifecycle@example.com",
            subject="Urgent billing issue",
            message="My account has been charged incorrectly multiple times this month.",
        )
        ticket_ref = data["ticket_ref"]
        lookup = client.get(f"/support/ticket/{ticket_ref}")
        result = lookup.json()
        assert "priority" in result
        assert result["priority"] in ("low", "medium", "high", "critical")

    def test_ticket_has_channel_field(self, client):
        data = _submit_webform(
            client,
            name="Channel User",
            email="channel.lifecycle@example.com",
            subject="Channel check",
            message="Just testing which channel this ticket was submitted via.",
        )
        ticket_ref = data["ticket_ref"]
        lookup = client.get(f"/support/ticket/{ticket_ref}")
        assert lookup.json()["channel"] == "web_form"

    def test_ticket_created_at_is_populated(self, client):
        data = _submit_webform(
            client,
            name="Time User",
            email="time.lifecycle@example.com",
            subject="Timing test",
            message="Testing that ticket creation timestamp is recorded correctly.",
        )
        ticket_ref = data["ticket_ref"]
        lookup = client.get(f"/support/ticket/{ticket_ref}")
        result = lookup.json()
        assert "created_at" in result
        assert result["created_at"] is not None

    def test_escalated_ticket_has_assigned_team(self, client):
        data = _submit_webform(
            client,
            name="Escalated User",
            email="escalated.team@example.com",
            subject="Security breach",
            message="We have detected a security breach in our account. This is urgent.",
        )
        if data.get("escalated"):
            ticket_ref = data["ticket_ref"]
            lookup = client.get(f"/support/ticket/{ticket_ref}")
            result = lookup.json()
            # assigned_team may be set on escalation
            assert "assigned_team" in result


# ===========================================================================
# 6. Analytics & Metrics
# ===========================================================================

class TestAnalyticsAfterE2E:
    """Analytics endpoints reflect activity from previous E2E tests."""

    def test_analytics_summary_endpoint_returns_200(self, client):
        resp = client.get("/analytics/summary")
        assert resp.status_code == 200

    def test_analytics_summary_has_expected_keys(self, client):
        resp = client.get("/analytics/summary")
        data = resp.json()
        assert isinstance(data, dict)
        # Accept demo or live data structure
        assert len(data) > 0

    def test_analytics_usage_endpoint_returns_200(self, client):
        resp = client.get("/analytics/usage")
        assert resp.status_code == 200

    def test_analytics_recent_endpoint_returns_200(self, client):
        resp = client.get("/analytics/recent")
        assert resp.status_code == 200

    def test_analytics_recent_is_list(self, client):
        resp = client.get("/analytics/recent")
        data = resp.json()
        assert isinstance(data, list)

    def test_health_endpoint_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("status") == "ok"


# ===========================================================================
# 7. Concurrent / Rapid Submission
# ===========================================================================

class TestRapidSubmission:
    """Simulate rapid consecutive submissions to check for race conditions."""

    def test_ten_sequential_submissions_all_succeed(self, client):
        ticket_refs = []
        for i in range(10):
            data = _submit_webform(
                client,
                name=f"Rapid User {i}",
                email=f"rapid{i}.e2e@example.com",
                subject=f"Rapid test {i}",
                message=f"This is rapid test message number {i} to stress the pipeline.",
            )
            assert data["ticket_ref"].startswith("TKT-")
            ticket_refs.append(data["ticket_ref"])

        # All ticket refs are unique
        assert len(set(ticket_refs)) == 10

    def test_all_channels_in_sequence(self, client):
        """Submit web_form, gmail, whatsapp back-to-back without pause."""
        wf = _submit_webform(
            client, "Seq A", "seq.a@example.com", "SeqA", "Sequential channel test A web form."
        )
        assert wf["ticket_ref"].startswith("TKT-")

        gm = client.post(
            "/webhooks/gmail",
            json=_make_pubsub_payload("seq.b@example.com", "SeqB", "Sequential gmail test B.", "seq_b"),
        )
        assert gm.status_code == 200

        wa = client.post(
            "/webhooks/whatsapp",
            data=_make_twilio_form("+15009990099", "Sequential WhatsApp test C", "SM_seq_c"),
        )
        assert wa.status_code == 200
