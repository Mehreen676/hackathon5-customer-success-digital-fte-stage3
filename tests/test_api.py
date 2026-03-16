"""
API Endpoint Tests — Customer Success Digital FTE (Stage 2)

Tests all /health and /support/* FastAPI endpoints using TestClient.
Uses an isolated in-memory SQLite database — no production data affected.

Run with:
    pytest tests/test_api.py -v
"""

import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.database import Base, get_db
from backend.mcp.tool_registry import init_tools


# ---------------------------------------------------------------------------
# Test database setup
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
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
    """Initialize DB schema and MCP tools once for the module."""
    from backend.database import models  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    init_tools()

    # Seed test data
    db = TestingSessionLocal()
    try:
        from backend.services.knowledge_service import seed_all
        seed_all(db)
    finally:
        db.close()


@pytest.fixture
def client():
    """Return a TestClient with the DB dependency overridden."""
    from backend.api.main import app
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        data = client.get("/health").json()
        assert "status" in data
        assert "version" in data
        assert "stage" in data
        assert "db" in data

    def test_health_status_is_ok(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_stage_is_2(self, client):
        data = client.get("/health").json()
        assert data["stage"] == "2"

    def test_health_db_connected(self, client):
        data = client.get("/health").json()
        assert data["db"] == "connected"


# ---------------------------------------------------------------------------
# POST /support/message tests
# ---------------------------------------------------------------------------

class TestGenericMessageEndpoint:

    def test_routine_message_returns_200(self, client):
        payload = {
            "customer_id": "CUST-001",
            "channel": "email",
            "content": "How do I reset my password?",
        }
        response = client.post("/support/message", json=payload)
        assert response.status_code == 200

    def test_response_has_required_fields(self, client):
        payload = {
            "customer_id": "CUST-001",
            "channel": "email",
            "content": "Where can I find my invoice?",
        }
        data = client.post("/support/message", json=payload).json()
        required = {"success", "channel", "customer", "escalated", "kb_used", "ticket", "response", "conversation_id"}
        assert required.issubset(set(data.keys()))

    def test_escalation_message_is_flagged(self, client):
        payload = {
            "customer_id": "CUST-002",
            "channel": "email",
            "content": "I want a full refund immediately.",
        }
        data = client.post("/support/message", json=payload).json()
        assert data["escalated"] is True
        assert data["escalation_reason"] == "refund_request"

    def test_routine_message_not_escalated(self, client):
        payload = {
            "customer_id": "CUST-001",
            "channel": "email",
            "content": "How do I add a new team member?",
        }
        data = client.post("/support/message", json=payload).json()
        assert data["escalated"] is False

    def test_kb_match_for_known_topic(self, client):
        payload = {
            "customer_id": "CUST-001",
            "channel": "web_form",
            "content": "How do I connect Slack to Nexora?",
        }
        data = client.post("/support/message", json=payload).json()
        assert data["kb_used"] is True

    def test_ticket_always_created(self, client):
        payload = {
            "customer_id": "CUST-003",
            "channel": "whatsapp",
            "content": "Hello, I need help please",
        }
        data = client.post("/support/message", json=payload).json()
        assert "ticket" in data
        assert data["ticket"]["ticket_ref"].startswith("TKT-")

    def test_invalid_channel_returns_error(self, client):
        payload = {
            "customer_id": "CUST-001",
            "channel": "fax",
            "content": "Hello",
        }
        response = client.post("/support/message", json=payload)
        assert response.status_code == 422

    def test_empty_content_rejected(self, client):
        payload = {
            "customer_id": "CUST-001",
            "channel": "email",
            "content": "",
        }
        response = client.post("/support/message", json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /support/gmail tests
# ---------------------------------------------------------------------------

class TestGmailEndpoint:

    def test_gmail_endpoint_returns_200(self, client):
        payload = {
            "from_email": "sarah.mitchell@brightflow.com",
            "from_name": "Sarah Mitchell",
            "subject": "Password reset help",
            "body": "Hi, I've forgotten my password. How do I reset it?",
            "customer_id": "CUST-001",
        }
        response = client.post("/support/gmail", json=payload)
        assert response.status_code == 200

    def test_gmail_channel_is_email(self, client):
        payload = {
            "from_email": "test@example.com",
            "from_name": "Test User",
            "subject": "Invoice query",
            "body": "Where can I find my invoice?",
        }
        data = client.post("/support/gmail", json=payload).json()
        assert data["channel"] == "email"

    def test_gmail_escalation_detected(self, client):
        payload = {
            "from_email": "angry@example.com",
            "from_name": "Angry Customer",
            "subject": "Legal Action",
            "body": "I will consult my attorney about legal action if this is not resolved.",
            "customer_id": "CUST-001",
        }
        data = client.post("/support/gmail", json=payload).json()
        assert data["escalated"] is True
        assert data["escalation_reason"] == "legal_complaint"

    def test_gmail_response_is_formal(self, client):
        payload = {
            "from_email": "user@company.com",
            "from_name": "Test User",
            "subject": "Help with account",
            "body": "How do I reset my password?",
        }
        data = client.post("/support/gmail", json=payload).json()
        assert "Dear" in data["response"] or "Thank you" in data["response"]


# ---------------------------------------------------------------------------
# POST /support/whatsapp tests
# ---------------------------------------------------------------------------

class TestWhatsAppEndpoint:

    def test_whatsapp_endpoint_returns_200(self, client):
        payload = {
            "from_phone": "+1-555-0101",
            "message_text": "Hi, I need my invoice please",
            "customer_id": "CUST-002",
        }
        response = client.post("/support/whatsapp", json=payload)
        assert response.status_code == 200

    def test_whatsapp_channel_is_whatsapp(self, client):
        payload = {
            "from_phone": "+1-555-0202",
            "message_text": "How do I cancel my subscription?",
        }
        data = client.post("/support/whatsapp", json=payload).json()
        assert data["channel"] == "whatsapp"

    def test_whatsapp_response_is_concise(self, client):
        payload = {
            "from_phone": "+1-555-0303",
            "message_text": "How do I reset my password?",
        }
        data = client.post("/support/whatsapp", json=payload).json()
        # WhatsApp responses should be shorter than email responses
        word_count = len(data["response"].split())
        assert word_count <= 150, f"WhatsApp response too long: {word_count} words"


# ---------------------------------------------------------------------------
# POST /support/webform tests
# ---------------------------------------------------------------------------

class TestWebFormEndpoint:

    def test_webform_endpoint_returns_200(self, client):
        payload = {
            "name": "Priya Sharma",
            "email": "priya@techbridge.net",
            "subject": "Integration question",
            "message": "How do I connect Slack to my Nexora workspace?",
            "customer_id": "CUST-003",
        }
        response = client.post("/support/webform", json=payload)
        assert response.status_code == 200

    def test_webform_channel_is_web_form(self, client):
        payload = {
            "name": "Test User",
            "email": "test@example.com",
            "subject": "General query",
            "message": "How do I export my data?",
        }
        data = client.post("/support/webform", json=payload).json()
        assert data["channel"] == "web_form"

    def test_webform_ticket_reference_in_response(self, client):
        payload = {
            "name": "James Okafor",
            "email": "james@deltaops.io",
            "subject": "Billing query",
            "message": "I need a copy of my invoice for last month.",
        }
        data = client.post("/support/webform", json=payload).json()
        ticket_ref = data["ticket"]["ticket_ref"]
        assert ticket_ref in data["response"]

    def test_webform_security_escalation(self, client):
        payload = {
            "name": "Worried User",
            "email": "worried@company.com",
            "subject": "Possible breach",
            "message": "I think my account was hacked. Someone logged in from another country.",
        }
        data = client.post("/support/webform", json=payload).json()
        assert data["escalated"] is True
        assert data["escalation_reason"] == "security_issue"


# ---------------------------------------------------------------------------
# Root and general tests
# ---------------------------------------------------------------------------

class TestRootEndpoint:

    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_service_info(self, client):
        data = client.get("/").json()
        assert "stage" in data
        assert data["stage"] == "2"
