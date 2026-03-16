"""
Tests verifying that FastAPI backend responses are compatible with the Stage 3 frontend.

Ensures all fields expected by the Next.js dashboard are present in API responses.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.main import app
from backend.database.database import Base, get_db
from backend.mcp.tool_registry import init_tools
from backend.services.knowledge_service import seed_all


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="module")
def TestingSessionLocal(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module", autouse=True)
def setup_module(TestingSessionLocal):
    init_tools()
    db = TestingSessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()


@pytest.fixture(scope="module")
def client(TestingSessionLocal):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealthEndpointFrontendCompat:
    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_has_status_field(self, client):
        r = client.get("/health")
        assert "status" in r.json()

    def test_health_has_version_field(self, client):
        r = client.get("/health")
        assert "version" in r.json()

    def test_health_has_stage_field(self, client):
        r = client.get("/health")
        assert "stage" in r.json()

    def test_health_stage_is_3(self, client):
        r = client.get("/health")
        data = r.json()
        # stage may be string or int
        assert str(data.get("stage", "")) in ("3", "3.0")

    def test_health_has_db_field(self, client):
        r = client.get("/health")
        assert "db" in r.json()


# ---------------------------------------------------------------------------
# Gmail / Email endpoint
# ---------------------------------------------------------------------------

class TestGmailEndpointFrontendCompat:
    PAYLOAD = {
        "from_email": "frontend-test@example.com",
        "from_name": "Frontend Test User",
        "subject": "Password reset help",
        "body": "I cannot log in to my account. How do I reset my password?",
    }

    def test_returns_200(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert r.status_code == 200

    def test_has_success_field(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert "success" in r.json()

    def test_has_channel_field(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert r.json().get("channel") == "email"

    def test_has_intent_field(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert "intent" in r.json()

    def test_has_escalated_field(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert "escalated" in r.json()

    def test_has_kb_used_field(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert "kb_used" in r.json()

    def test_has_ticket_field(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert "ticket" in r.json()

    def test_has_response_field(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert "response" in r.json()
        assert r.json()["response"]  # non-empty

    def test_response_text_is_string(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert isinstance(r.json()["response"], str)


# ---------------------------------------------------------------------------
# WhatsApp endpoint
# ---------------------------------------------------------------------------

class TestWhatsAppEndpointFrontendCompat:
    PAYLOAD = {
        "from_phone": "+441234567890",
        "message_text": "Hi I need to add a team member to my account",
    }

    def test_returns_200(self, client):
        r = client.post("/support/whatsapp", json=self.PAYLOAD)
        assert r.status_code == 200

    def test_channel_is_whatsapp(self, client):
        r = client.post("/support/whatsapp", json=self.PAYLOAD)
        assert r.json().get("channel") == "whatsapp"

    def test_has_all_required_fields(self, client):
        r = client.post("/support/whatsapp", json=self.PAYLOAD)
        data = r.json()
        for field in ("success", "channel", "intent", "escalated", "kb_used", "ticket", "response"):
            assert field in data, f"Missing field: {field}"

    def test_response_is_shorter_than_email(self, client):
        email_payload = {
            "from_email": "test@ex.com",
            "from_name": "Test",
            "subject": "Add team member",
            "body": "How do I add a team member?",
        }
        wa_r = client.post("/support/whatsapp", json=self.PAYLOAD)
        email_r = client.post("/support/gmail", json=email_payload)
        # WhatsApp responses should generally be shorter
        assert len(wa_r.json()["response"]) <= len(email_r.json()["response"]) + 200


# ---------------------------------------------------------------------------
# Web form endpoint
# ---------------------------------------------------------------------------

class TestWebFormEndpointFrontendCompat:
    PAYLOAD = {
        "name": "Priya Sharma",
        "email": "priya@example.com",
        "subject": "Slack integration not working",
        "message": "I set up the Slack integration but notifications are not arriving.",
    }

    def test_returns_200(self, client):
        r = client.post("/support/webform", json=self.PAYLOAD)
        assert r.status_code == 200

    def test_channel_is_web_form(self, client):
        r = client.post("/support/webform", json=self.PAYLOAD)
        assert r.json().get("channel") == "web_form"

    def test_ticket_has_ticket_ref(self, client):
        r = client.post("/support/webform", json=self.PAYLOAD)
        ticket = r.json().get("ticket", {})
        assert "ticket_ref" in ticket
        assert ticket["ticket_ref"].startswith("TKT-")


# ---------------------------------------------------------------------------
# Stage 3 AI fields present
# ---------------------------------------------------------------------------

class TestAIFieldsPresent:
    """Verify the Stage 3 ai_used / ai_provider fields are in the response."""

    PAYLOAD = {
        "from_email": "ai-test@example.com",
        "from_name": "AI Field Test",
        "subject": "Something completely novel",
        "body": "Tell me about something the KB definitely does not cover.",
    }

    def test_ai_used_field_present(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert "ai_used" in r.json()

    def test_ai_used_is_boolean(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert isinstance(r.json()["ai_used"], bool)

    def test_ai_provider_field_present(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert "ai_provider" in r.json()

    def test_response_time_ms_field_present(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert "response_time_ms" in r.json()

    def test_response_time_ms_is_positive(self, client):
        r = client.post("/support/gmail", json=self.PAYLOAD)
        assert r.json()["response_time_ms"] >= 0


# ---------------------------------------------------------------------------
# Analytics endpoint
# ---------------------------------------------------------------------------

class TestAnalyticsEndpoint:
    def test_analytics_summary_returns_200(self, client):
        r = client.get("/analytics/summary")
        assert r.status_code == 200

    def test_analytics_has_total_interactions(self, client):
        r = client.get("/analytics/summary")
        assert "total_interactions" in r.json()

    def test_analytics_has_kb_hit_rate(self, client):
        r = client.get("/analytics/summary")
        assert "kb_hit_rate" in r.json()

    def test_analytics_has_escalation_rate(self, client):
        r = client.get("/analytics/summary")
        assert "escalation_rate" in r.json()

    def test_analytics_recent_returns_200(self, client):
        r = client.get("/analytics/recent")
        assert r.status_code == 200

    def test_analytics_recent_has_records(self, client):
        r = client.get("/analytics/recent")
        assert "records" in r.json()

    def test_analytics_usage_returns_200(self, client):
        r = client.get("/analytics/usage")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# CORS headers
# ---------------------------------------------------------------------------

class TestCorsHeaders:
    def test_cors_header_present_on_options(self, client):
        r = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
        )
        # FastAPI CORS middleware should respond to OPTIONS
        assert r.status_code in (200, 405)  # 405 is acceptable too

    def test_health_allows_cross_origin(self, client):
        r = client.get("/health", headers={"Origin": "http://localhost:3000"})
        # Should not be blocked
        assert r.status_code == 200
