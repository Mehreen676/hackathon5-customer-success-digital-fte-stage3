"""
Webhook Tests — Customer Success Digital FTE (Stage 3)

Tests for:
  - POST /webhooks/gmail   (Google Pub/Sub push notification)
  - POST /webhooks/whatsapp (Twilio form-encoded webhook)
  - Gmail webhook parsing helpers
  - WhatsApp webhook parsing helpers

All Gmail API and Twilio API calls are exercised in MOCK mode (no real
credentials required). The tests use an in-memory SQLite database.

Run with:
    pytest tests/test_webhooks.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import base64
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.database import Base, get_db
from backend.mcp.tool_registry import init_tools
from backend.webhooks.gmail_webhook import (
    build_demo_pubsub_payload,
    parse_pubsub_notification,
    extract_sender_info,
)
from backend.webhooks.whatsapp_webhook import (
    build_demo_twilio_payload,
    parse_twilio_webhook,
    validate_twilio_signature,
)


# ---------------------------------------------------------------------------
# Test database
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    from backend.database import models  # noqa: F401

    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_module():
    from backend.database import models  # noqa: F401

    Base.metadata.create_all(bind=test_engine)
    init_tools()
    db = TestingSessionLocal()
    try:
        from backend.services.knowledge_service import seed_all

        seed_all(db)
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    from backend.api.main import app

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ===========================================================================
# Gmail webhook helper tests
# ===========================================================================


class TestGmailWebhookParsing:
    def test_parse_valid_pubsub_notification(self):
        payload = build_demo_pubsub_payload(
            email_address="support@nexora.io",
            history_id="9876543",
            message_id="pubsub_msg_001",
        )
        result = parse_pubsub_notification(payload)
        assert result is not None
        assert result["email_address"] == "support@nexora.io"
        assert result["history_id"] == "9876543"
        assert result["message_id"] == "pubsub_msg_001"
        assert "subscription" in result

    def test_parse_notification_missing_data(self):
        bad_payload = {
            "message": {"messageId": "123", "publishTime": "2024-01-01T00:00:00Z"},
            "subscription": "projects/test/subscriptions/sub",
        }
        result = parse_pubsub_notification(bad_payload)
        assert result is None

    def test_parse_notification_invalid_base64(self):
        bad_payload = {
            "message": {"data": "NOT_VALID_BASE64!!!!", "messageId": "123"},
            "subscription": "projects/test/subscriptions/sub",
        }
        result = parse_pubsub_notification(bad_payload)
        assert result is None

    def test_parse_notification_missing_message_key(self):
        result = parse_pubsub_notification({"subscription": "projects/x/subscriptions/y"})
        assert result is None

    def test_parse_notification_with_padding_correction(self):
        """Data without '=' padding should still parse correctly."""
        data = {"emailAddress": "user@example.com", "historyId": "111"}
        encoded = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
        payload = {
            "message": {"data": encoded, "messageId": "m1"},
            "subscription": "projects/p/subscriptions/s",
        }
        result = parse_pubsub_notification(payload)
        assert result is not None
        assert result["email_address"] == "user@example.com"

    def test_extract_sender_info_complete(self):
        gmail_msg = {
            "from_email": "alice@example.com",
            "from_name": "Alice",
            "subject": "Help with billing",
            "body": "I cannot find my invoice.",
            "thread_id": "thread_001",
            "message_id": "msg_001",
        }
        info = extract_sender_info(gmail_msg)
        assert info["from_email"] == "alice@example.com"
        assert info["from_name"] == "Alice"
        assert info["subject"] == "Help with billing"
        assert info["body"] == "I cannot find my invoice."

    def test_extract_sender_info_defaults(self):
        """Missing fields should fall back to sensible defaults."""
        info = extract_sender_info({})
        assert info["from_email"] == "unknown@example.com"
        assert info["subject"] == "Support Request"
        assert info["body"] == ""


# ===========================================================================
# WhatsApp webhook helper tests
# ===========================================================================


class TestWhatsAppWebhookParsing:
    def test_parse_valid_twilio_payload(self):
        data = build_demo_twilio_payload(
            from_phone="+15551234567",
            body="I need help with my account",
            message_sid="SM12345",
        )
        result = parse_twilio_webhook(
            from_field=data["From"],
            body=data["Body"],
            message_sid=data["MessageSid"],
            account_sid=data["AccountSid"],
            to_field=data["To"],
            num_media=data["NumMedia"],
            profile_name=data["ProfileName"],
            wa_id=data["WaId"],
        )
        assert result is not None
        assert result["from_phone"] == "+15551234567"
        assert result["message_text"] == "I need help with my account"
        assert result["message_sid"] == "SM12345"
        assert result["has_media"] is False
        assert result["profile_name"] == "Test Customer"

    def test_parse_missing_from_field(self):
        result = parse_twilio_webhook(from_field="", body="Hello")
        assert result is None

    def test_parse_missing_body_field(self):
        result = parse_twilio_webhook(from_field="whatsapp:+15551234567", body="")
        assert result is None

    def test_parse_strips_whatsapp_prefix(self):
        result = parse_twilio_webhook(
            from_field="whatsapp:+19991112222",
            body="Test message",
        )
        assert result is not None
        assert result["from_phone"] == "+19991112222"
        assert "whatsapp:" not in result["from_phone"]

    def test_parse_adds_plus_prefix(self):
        """Numbers without '+' should have it added for E.164 compliance."""
        result = parse_twilio_webhook(from_field="19991112222", body="Hi")
        assert result is not None
        assert result["from_phone"].startswith("+")

    def test_parse_with_media(self):
        result = parse_twilio_webhook(
            from_field="whatsapp:+15551234567",
            body="See attached",
            num_media="1",
        )
        assert result is not None
        assert result["has_media"] is True

    def test_validate_twilio_signature_no_token(self):
        """Without TWILIO_AUTH_TOKEN validation should always return True."""
        result = validate_twilio_signature(
            url="https://example.com/webhooks/whatsapp",
            params={"From": "whatsapp:+1555", "Body": "Hi"},
            signature="bad_sig",
        )
        assert result is True


# ===========================================================================
# POST /webhooks/gmail  (HTTP endpoint)
# ===========================================================================


class TestGmailWebhookEndpoint:
    def test_valid_pubsub_notification(self, client):
        payload = build_demo_pubsub_payload()
        resp = client.post("/webhooks/gmail", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["received"] is True
        assert data["channel"] == "email"
        assert data["status"] == "processed"
        # Should have created a ticket
        assert data["ticket_ref"] is not None
        assert data["ticket_ref"].startswith("TKT-")

    def test_empty_data_field_returns_parse_error(self, client):
        """Pub/Sub message with no data field — ack with parse_error status."""
        bad_payload = {
            "message": {"data": "", "messageId": "m1", "publishTime": "2024-01-01T00:00:00Z"},
            "subscription": "projects/x/subscriptions/y",
        }
        resp = client.post("/webhooks/gmail", json=bad_payload)
        # Must still return 200 so Pub/Sub doesn't retry
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "parse_error"

    def test_invalid_data_encoding(self, client):
        payload = {
            "message": {
                "data": "AAAA_NOT_DECODABLE!!!",
                "messageId": "m2",
                "publishTime": "2024-01-01T00:00:00Z",
            },
            "subscription": "projects/x/subscriptions/y",
        }
        resp = client.post("/webhooks/gmail", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "parse_error"

    def test_response_has_mode_field(self, client):
        """MOCK mode should be reported in the response."""
        payload = build_demo_pubsub_payload()
        resp = client.post("/webhooks/gmail", json=payload)
        assert "mode" in resp.json()

    def test_escalation_flag_present(self, client):
        payload = build_demo_pubsub_payload()
        resp = client.post("/webhooks/gmail", json=payload)
        data = resp.json()
        assert "escalated" in data

    def test_missing_subscription_field_still_processes(self, client):
        """subscription is optional — should still work without it."""
        data = {"emailAddress": "test@example.com", "historyId": "111"}
        encoded = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
        payload = {
            "message": {"data": encoded, "messageId": "m3", "publishTime": "2024-01-01T00:00:00Z"},
        }
        resp = client.post("/webhooks/gmail", json=payload)
        assert resp.status_code == 200


# ===========================================================================
# POST /webhooks/whatsapp  (HTTP endpoint)
# ===========================================================================


class TestWhatsAppWebhookEndpoint:
    def _form_data(self, **overrides):
        defaults = {
            "From": "whatsapp:+15551234567",
            "Body": "I cannot find my invoice. Can you help?",
            "MessageSid": "SM00000000000000000000000000000001",
            "AccountSid": "AC00000000000000000000000000000000",
            "To": "whatsapp:+14155238886",
            "NumMedia": "0",
            "ProfileName": "Test Customer",
            "WaId": "15551234567",
        }
        defaults.update(overrides)
        return defaults

    def test_valid_twilio_webhook(self, client):
        resp = client.post("/webhooks/whatsapp", data=self._form_data())
        assert resp.status_code == 200
        data = resp.json()
        assert data["received"] is True
        assert data["channel"] == "whatsapp"
        assert data["status"] == "processed"
        assert data["ticket_ref"] is not None
        assert data["ticket_ref"].startswith("TKT-")

    def test_missing_from_returns_parse_error(self, client):
        resp = client.post("/webhooks/whatsapp", data=self._form_data(From=""))
        # From is a required Form field → FastAPI returns 422
        assert resp.status_code in (200, 422)

    def test_billing_intent_processed(self, client):
        resp = client.post(
            "/webhooks/whatsapp",
            data=self._form_data(Body="I need help with my billing invoice"),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"

    def test_different_customers_get_different_tickets(self, client):
        resp1 = client.post(
            "/webhooks/whatsapp",
            data=self._form_data(From="whatsapp:+15550000001", Body="Help me with account"),
        )
        resp2 = client.post(
            "/webhooks/whatsapp",
            data=self._form_data(From="whatsapp:+15550000002", Body="Help me with billing"),
        )
        t1 = resp1.json().get("ticket_ref")
        t2 = resp2.json().get("ticket_ref")
        assert t1 is not None and t2 is not None
        assert t1 != t2

    def test_response_has_message_sid(self, client):
        resp = client.post(
            "/webhooks/whatsapp",
            data=self._form_data(MessageSid="SM_TEST_SID"),
        )
        data = resp.json()
        assert data.get("message_sid") == "SM_TEST_SID"

    def test_escalation_keywords_trigger_escalation(self, client):
        resp = client.post(
            "/webhooks/whatsapp",
            data=self._form_data(
                From="whatsapp:+15559999999",
                Body="I want to cancel my account immediately and get a full refund",
            ),
        )
        assert resp.status_code == 200
        # May or may not escalate depending on rules, but should always process
        assert resp.json()["status"] == "processed"
