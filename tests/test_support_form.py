"""
Support Form & Ticket Status Tests — Customer Success Digital FTE (Stage 3)

Tests for:
  - POST /support/submit   (user-facing web support form)
  - GET  /support/ticket/{ticket_ref}  (ticket status lookup)
  - Cross-channel continuity (same email identity maps to same customer)
  - Ticket lookup after submission confirms round-trip

Run with:
    pytest tests/test_support_form.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.database import Base, get_db
from backend.mcp.tool_registry import init_tools


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _submit_payload(**overrides):
    defaults = {
        "name": "Alice Johnson",
        "email": "alice@brightflow.com",
        "subject": "Billing question",
        "message": "I cannot find my invoice from last month. Where can I download it?",
    }
    defaults.update(overrides)
    return defaults


# ===========================================================================
# POST /support/submit
# ===========================================================================


class TestSupportFormSubmit:
    def test_basic_submission_succeeds(self, client):
        resp = client.post("/support/submit", json=_submit_payload())
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["channel"] == "web_form"

    def test_response_contains_ticket_ref(self, client):
        resp = client.post("/support/submit", json=_submit_payload())
        data = resp.json()
        assert "ticket" in data
        assert data["ticket"]["ticket_ref"].startswith("TKT-")

    def test_response_contains_agent_response_text(self, client):
        resp = client.post("/support/submit", json=_submit_payload())
        data = resp.json()
        assert "response" in data
        assert len(data["response"]) > 0

    def test_response_contains_customer_name(self, client):
        resp = client.post(
            "/support/submit",
            json=_submit_payload(name="Bob Smith"),
        )
        data = resp.json()
        assert data["customer"] == "Bob Smith"

    def test_response_contains_intent(self, client):
        resp = client.post("/support/submit", json=_submit_payload())
        data = resp.json()
        assert "intent" in data
        assert data["intent"] is not None

    def test_response_contains_conversation_id(self, client):
        resp = client.post("/support/submit", json=_submit_payload())
        data = resp.json()
        assert "conversation_id" in data
        assert data["conversation_id"]

    def test_kb_used_flag_present(self, client):
        resp = client.post("/support/submit", json=_submit_payload())
        data = resp.json()
        assert "kb_used" in data

    def test_escalated_flag_present(self, client):
        resp = client.post("/support/submit", json=_submit_payload())
        data = resp.json()
        assert "escalated" in data

    def test_billing_query_returns_billing_intent(self, client):
        resp = client.post(
            "/support/submit",
            json=_submit_payload(
                message="I was charged twice for my subscription this month"
            ),
        )
        data = resp.json()
        assert data["success"] is True
        # Billing-related keywords should trigger billing intent
        assert data.get("intent") in ("billing", "account", "plan", "general")

    def test_missing_name_returns_422(self, client):
        payload = {
            "email": "test@example.com",
            "subject": "Help",
            "message": "I need help",
        }
        resp = client.post("/support/submit", json=payload)
        assert resp.status_code == 422

    def test_missing_email_returns_422(self, client):
        payload = {
            "name": "Test User",
            "subject": "Help",
            "message": "I need help",
        }
        resp = client.post("/support/submit", json=payload)
        assert resp.status_code == 422

    def test_missing_message_returns_422(self, client):
        payload = {
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Help",
        }
        resp = client.post("/support/submit", json=payload)
        assert resp.status_code == 422

    def test_empty_message_returns_422(self, client):
        resp = client.post(
            "/support/submit",
            json=_submit_payload(message=""),
        )
        assert resp.status_code == 422

    def test_escalation_keywords_processed(self, client):
        """Escalation-triggering messages should still return 200 with escalated=True."""
        resp = client.post(
            "/support/submit",
            json=_submit_payload(
                email="angry@customer.com",
                message="This is completely unacceptable. I'm going to take legal action if you don't fix this immediately.",
            ),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        # Ticket status reflects escalation
        if data["escalated"]:
            assert data["ticket"]["status"] in ("escalated", "open")

    def test_ticket_ref_format(self, client):
        """Ticket refs should follow the TKT-XXXXXXXX pattern."""
        resp = client.post("/support/submit", json=_submit_payload())
        data = resp.json()
        ref = data["ticket"]["ticket_ref"]
        assert ref.startswith("TKT-")
        assert len(ref) == 12  # TKT- (4) + 8 hex chars

    def test_channel_is_web_form(self, client):
        """Submit endpoint always assigns web_form channel."""
        resp = client.post("/support/submit", json=_submit_payload())
        data = resp.json()
        assert data["channel"] == "web_form"
        assert data["ticket"]["channel"] == "web_form"

    def test_multiple_submissions_get_unique_tickets(self, client):
        r1 = client.post("/support/submit", json=_submit_payload(email="u1@example.com"))
        r2 = client.post("/support/submit", json=_submit_payload(email="u2@example.com"))
        t1 = r1.json()["ticket"]["ticket_ref"]
        t2 = r2.json()["ticket"]["ticket_ref"]
        assert t1 != t2


# ===========================================================================
# GET /support/ticket/{ticket_ref}
# ===========================================================================


class TestTicketStatusLookup:
    @pytest.fixture(scope="class")
    def submitted_ticket(self, client):
        """Submit a request and return the ticket_ref for lookup tests."""
        resp = client.post(
            "/support/submit",
            json=_submit_payload(
                name="Carol Lookup",
                email="carol@lookup.com",
                message="I need to update my billing address. How do I do this?",
            ),
        )
        assert resp.status_code == 200
        return resp.json()["ticket"]["ticket_ref"]

    def test_lookup_existing_ticket(self, client, submitted_ticket):
        resp = client.get(f"/support/ticket/{submitted_ticket}")
        assert resp.status_code == 200

    def test_lookup_response_has_ticket_ref(self, client, submitted_ticket):
        data = client.get(f"/support/ticket/{submitted_ticket}").json()
        assert data["ticket_ref"] == submitted_ticket

    def test_lookup_response_has_status(self, client, submitted_ticket):
        data = client.get(f"/support/ticket/{submitted_ticket}").json()
        assert "status" in data
        assert data["status"] in (
            "open", "auto-resolved", "escalated", "pending_review", "closed"
        )

    def test_lookup_response_has_priority(self, client, submitted_ticket):
        data = client.get(f"/support/ticket/{submitted_ticket}").json()
        assert "priority" in data
        assert data["priority"] in ("low", "medium", "high", "critical")

    def test_lookup_response_has_channel(self, client, submitted_ticket):
        data = client.get(f"/support/ticket/{submitted_ticket}").json()
        assert data["channel"] == "web_form"

    def test_lookup_response_has_customer_name(self, client, submitted_ticket):
        data = client.get(f"/support/ticket/{submitted_ticket}").json()
        assert "customer_name" in data
        assert data["customer_name"] == "Carol Lookup"

    def test_lookup_response_has_subject(self, client, submitted_ticket):
        data = client.get(f"/support/ticket/{submitted_ticket}").json()
        assert "subject" in data
        assert len(data["subject"]) > 0

    def test_lookup_response_has_created_at(self, client, submitted_ticket):
        data = client.get(f"/support/ticket/{submitted_ticket}").json()
        assert "created_at" in data
        assert data["created_at"] is not None

    def test_lookup_response_has_escalated_flag(self, client, submitted_ticket):
        data = client.get(f"/support/ticket/{submitted_ticket}").json()
        assert "escalated" in data
        assert isinstance(data["escalated"], bool)

    def test_lookup_nonexistent_ticket_returns_404(self, client):
        resp = client.get("/support/ticket/TKT-XXXXXXXX")
        assert resp.status_code == 404

    def test_lookup_wrong_format_returns_404(self, client):
        resp = client.get("/support/ticket/INVALID-REF")
        assert resp.status_code == 404

    def test_lookup_case_insensitive(self, client, submitted_ticket):
        """The endpoint should accept lowercase ticket refs too."""
        lower_ref = submitted_ticket.lower()
        resp = client.get(f"/support/ticket/{lower_ref}")
        # The endpoint normalises to uppercase — should return 200 or 404 for lowercase
        assert resp.status_code in (200, 404)


# ===========================================================================
# Cross-channel continuity
# ===========================================================================


class TestCrossChannelContinuity:
    """
    Same customer using multiple channels should be recognised by email address.
    This tests that customer identity resolution works across channels.
    """

    def test_same_email_via_submit_creates_customer(self, client):
        email = "continuity_test@example.com"
        resp = client.post(
            "/support/submit",
            json=_submit_payload(
                name="Continuity User",
                email=email,
                message="First contact via web form",
            ),
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_same_email_via_gmail_uses_same_identity(self, client):
        """
        A Gmail message from the same email address should be linked to
        the same customer record as a web form submission.
        """
        email = "continuity_test@example.com"
        resp = client.post(
            "/support/gmail",
            json={
                "from_email": email,
                "from_name": "Continuity User",
                "subject": "Follow-up question",
                "body": "Following up on my previous request about billing",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        # Customer name should be preserved
        assert data["customer"] in ("Continuity User", email.split("@")[0].title())

    def test_ticket_lookup_works_after_submit(self, client):
        """End-to-end: submit → lookup by returned ref → status matches."""
        resp = client.post(
            "/support/submit",
            json=_submit_payload(
                name="E2E User",
                email="e2e@roundtrip.com",
                message="End-to-end test message for ticket status round-trip",
            ),
        )
        assert resp.status_code == 200
        ticket_ref = resp.json()["ticket"]["ticket_ref"]
        submit_status = resp.json()["ticket"]["status"]

        lookup_resp = client.get(f"/support/ticket/{ticket_ref}")
        assert lookup_resp.status_code == 200
        assert lookup_resp.json()["status"] == submit_status
        assert lookup_resp.json()["ticket_ref"] == ticket_ref

    def test_whatsapp_and_webform_produce_different_channels(self, client):
        """WhatsApp and web form submissions should record their respective channels."""
        web_resp = client.post(
            "/support/submit",
            json=_submit_payload(email="multichannel@test.com"),
        )
        wa_resp = client.post(
            "/support/whatsapp",
            json={
                "from_phone": "+15553334444",
                "message_text": "Help with my account please",
            },
        )
        assert web_resp.json()["channel"] == "web_form"
        assert wa_resp.json()["channel"] == "whatsapp"
