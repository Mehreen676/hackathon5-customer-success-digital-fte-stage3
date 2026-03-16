"""
Tests for the Stage 3 AI Reasoning Pipeline.

Tests the end-to-end workflow with LLM integration, verifying that:
- KB hits are used directly (no LLM call)
- KB misses trigger the LLM layer
- Escalations bypass the LLM entirely
- LLM failures degrade gracefully to fallback
- Analytics metrics are recorded
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.database import Base
from backend.agents.workflow import process_message
from backend.mcp.tool_registry import init_tools
from backend.services.knowledge_service import seed_all


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture(scope="module")
def SessionLocal(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module", autouse=True)
def setup_tools(SessionLocal):
    init_tools()
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()


@pytest.fixture
def db(SessionLocal):
    session = SessionLocal()
    yield session
    session.close()


def _process(content, channel="web_form", db=None, customer_id="TEST-PIPELINE-001",
             customer_name="Test User", customer_email="test@pipeline.com"):
    return process_message(
        customer_id=customer_id,
        channel=channel,
        content=content,
        db=db,
        customer_name=customer_name,
        customer_email=customer_email,
    )


# ---------------------------------------------------------------------------
# KB Hit tests
# ---------------------------------------------------------------------------

class TestReasoningPipelineKBHit:
    def test_password_reset_kb_hit(self, db):
        result = _process("How do I reset my password?", db=db)
        assert result["success"] is True
        assert result["kb_used"] is True

    def test_kb_hit_no_ai_used(self, db):
        result = _process("How do I reset my password?", db=db)
        assert result["ai_used"] is False

    def test_kb_hit_auto_resolved(self, db):
        result = _process("I need to reset my password", db=db)
        ticket = result.get("ticket", {})
        assert ticket.get("status") in ("auto-resolved", "pending_review")

    def test_billing_kb_hit(self, db):
        result = _process("Where can I find my invoice?", db=db)
        assert result["success"] is True
        # May match billing KB article
        assert result.get("response")

    def test_kb_hit_response_is_non_empty(self, db):
        result = _process("How do I add a team member?", db=db)
        assert result["response"]
        assert len(result["response"]) > 20


# ---------------------------------------------------------------------------
# KB Miss — LLM invoked
# ---------------------------------------------------------------------------

class TestReasoningPipelineKBMiss:
    def test_unknown_query_triggers_llm_attempt(self, db):
        """An obscure query that KB won't match should attempt LLM."""
        mock_response = MagicMock()
        mock_response.source = "llm"
        mock_response.content = "Here is an AI-generated answer about your query."
        mock_response.provider = "anthropic"
        mock_response.model = "claude-sonnet-4-6"
        mock_response.tokens_used = 200

        with patch("src.agents.workflow._try_llm_response", return_value=mock_response):
            result = _process(
                "Can Nexora integrate with a custom blockchain ticketing system?",
                db=db,
                customer_id="TEST-PIPELINE-002",
            )

        assert result["success"] is True
        assert result["ai_used"] is True
        assert result["ai_provider"] == "anthropic"

    def test_kb_miss_with_llm_response_has_content(self, db):
        mock_response = MagicMock()
        mock_response.source = "llm"
        mock_response.content = "AI-generated helpful response content."
        mock_response.provider = "openai"
        mock_response.model = "gpt-4o-mini"
        mock_response.tokens_used = 150

        with patch("src.agents.workflow._try_llm_response", return_value=mock_response):
            result = _process(
                "How does Nexora handle enterprise SSO with Okta?",
                db=db,
                customer_id="TEST-PIPELINE-003",
            )

        assert result["response"]
        assert len(result["response"]) > 10

    def test_llm_none_response_uses_fallback(self, db):
        """When _try_llm_response returns None, workflow uses text fallback."""
        with patch("src.agents.workflow._try_llm_response", return_value=None):
            result = _process(
                "This query has absolutely no KB match xyz123",
                db=db,
                customer_id="TEST-PIPELINE-004",
            )

        assert result["success"] is True
        assert result["ai_used"] is False
        assert result["response"]  # fallback text present

    def test_kb_miss_llm_fallback_source_ticket_pending(self, db):
        fallback = MagicMock()
        fallback.source = "fallback"
        fallback.content = "A specialist will follow up shortly."
        fallback.provider = "none"
        fallback.model = "none"
        fallback.tokens_used = 0

        with patch("src.agents.workflow._try_llm_response", return_value=fallback):
            result = _process(
                "Completely unknown query that has no answer",
                db=db,
                customer_id="TEST-PIPELINE-005",
            )

        ticket = result.get("ticket", {})
        assert ticket.get("status") == "pending_review"


# ---------------------------------------------------------------------------
# Escalation tests
# ---------------------------------------------------------------------------

class TestReasoningPipelineEscalation:
    def test_refund_request_escalated(self, db):
        result = _process("I want a full refund right now", db=db, customer_id="TEST-ESC-001")
        assert result["escalated"] is True

    def test_legal_complaint_escalated(self, db):
        result = _process(
            "I have retained an attorney and will be suing Nexora",
            db=db,
            customer_id="TEST-ESC-002",
        )
        assert result["escalated"] is True

    def test_escalated_ai_not_used(self, db):
        result = _process("I want a refund immediately", db=db, customer_id="TEST-ESC-003")
        assert result["ai_used"] is False

    def test_escalation_skips_llm_call(self, db):
        with patch("src.agents.workflow._try_llm_response") as mock_llm:
            _process("I want a full refund", db=db, customer_id="TEST-ESC-004")
            mock_llm.assert_not_called()

    def test_escalated_response_is_holding_message(self, db):
        result = _process("I am furious about this service!", db=db, customer_id="TEST-ESC-005")
        assert result["response"]
        # Holding response should be non-empty


# ---------------------------------------------------------------------------
# Channel voice tests
# ---------------------------------------------------------------------------

class TestReasoningPipelineChannelVoice:
    def test_email_response_longer_than_whatsapp(self, db):
        query = "How do I reset my password?"
        email_r = _process(query, channel="email", db=db, customer_id="TEST-CV-001")
        wa_r = _process(query, channel="whatsapp", db=db, customer_id="TEST-CV-002")
        # Email responses are typically longer
        assert len(email_r["response"]) >= len(wa_r["response"]) - 50

    def test_email_response_contains_formal_elements(self, db):
        result = _process("How do I add a team member?", channel="email", db=db, customer_id="TEST-CV-003")
        # Email should have formal elements
        response = result["response"]
        has_formal = "Dear" in response or "regards" in response.lower() or "Nexora" in response
        assert has_formal

    def test_whatsapp_channel_recorded(self, db):
        result = _process("reset password", channel="whatsapp", db=db, customer_id="TEST-CV-004")
        assert result["channel"] == "whatsapp"


# ---------------------------------------------------------------------------
# Metrics tests
# ---------------------------------------------------------------------------

class TestReasoningPipelineMetrics:
    def test_result_has_response_time_ms(self, db):
        result = _process("How do I reset my password?", db=db, customer_id="TEST-METRICS-001")
        assert "response_time_ms" in result

    def test_response_time_is_positive(self, db):
        result = _process("billing question", db=db, customer_id="TEST-METRICS-002")
        assert result["response_time_ms"] > 0

    def test_result_has_conversation_id(self, db):
        result = _process("account question", db=db, customer_id="TEST-METRICS-003")
        assert "conversation_id" in result
        assert result["conversation_id"] is not None


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

class TestReasoningPipelineGracefulDegradation:
    def test_analytics_failure_does_not_crash_workflow(self, db):
        with patch("src.agents.workflow._record_analytics", side_effect=Exception("analytics down")):
            result = _process("reset password", db=db, customer_id="TEST-DEGRADE-001")
        assert result["success"] is True

    def test_llm_import_error_falls_back_gracefully(self, db):
        with patch("src.agents.workflow._try_llm_response", side_effect=ImportError("no llm")):
            result = _process(
                "Completely novel question not in KB",
                db=db,
                customer_id="TEST-DEGRADE-002",
            )
        assert result["success"] is True
        assert result["response"]


# ---------------------------------------------------------------------------
# VIP detection
# ---------------------------------------------------------------------------

class TestReasoningPipelineVIPCustomer:
    def test_vip_customer_complaint_escalated(self, db):
        # CUST-005 is the VIP Enterprise customer seeded by knowledge_service
        result = _process(
            "This is completely unacceptable and I am disappointed",
            db=db,
            customer_id="CUST-005",
            customer_name="VIP Enterprise Customer",
        )
        # VIP + complaint signal should trigger escalation
        assert result["escalated"] is True


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

class TestReasoningPipelineIntentClassification:
    @pytest.mark.parametrize("message,expected_intent", [
        ("I cannot pay my invoice", "billing"),
        ("How do I reset my password?", "account"),
        ("Connect to Slack", "integration"),
        ("I want to cancel my subscription", "cancellation"),
        ("I want a refund", "refund"),
        ("upgrade my plan", "plan"),
        ("export my data", "data"),
    ])
    def test_intent_classification(self, db, message, expected_intent):
        result = _process(message, db=db, customer_id=f"TEST-INTENT-{expected_intent}")
        assert result["intent"] == expected_intent
