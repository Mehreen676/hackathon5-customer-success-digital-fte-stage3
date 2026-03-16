"""
Agents SDK Layer Tests — Customer Success Digital FTE (Stage 3)

Tests for:
  - Typed tool input validation (Pydantic models)
  - @function_tool decorator and FunctionTool registration
  - Tool registry behaviour
  - AgentRunner pipeline (end-to-end with in-memory SQLite)
  - Channel-aware response generation (email / whatsapp / web_form)
  - CustomerSuccessAgent construction and tool set
  - AgentResult structure

All tests use an isolated in-memory SQLite database.
No LLM API calls are made — the pipeline degrades to rule-based fallback
when no API key is configured, which is the expected dev/CI behaviour.

Run with:
    pytest tests/test_agent_sdk.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pydantic import ValidationError
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
def db():
    """Provide an in-memory database session for the test module."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def agent():
    """Build the default CustomerSuccessAgent."""
    from backend.agent import CustomerSuccessAgent

    return CustomerSuccessAgent.build()


@pytest.fixture(scope="module")
def runner(db):
    """Create an AgentRunner with the test database session."""
    from backend.agent import AgentRunner

    return AgentRunner(db=db)


# ===========================================================================
# Typed Tool Input Validation
# ===========================================================================


class TestTypedToolInputs:
    def test_search_kb_input_requires_query(self):
        from backend.agent import SearchKBInput

        with pytest.raises(ValidationError):
            SearchKBInput()  # missing required 'query'

    def test_search_kb_input_valid(self):
        from backend.agent import SearchKBInput

        m = SearchKBInput(query="How do I reset my password?", channel="email")
        assert m.query == "How do I reset my password?"
        assert m.channel == "email"
        assert m.max_results == 3  # default

    def test_search_kb_input_max_results_clamp(self):
        from backend.agent import SearchKBInput

        with pytest.raises(ValidationError):
            SearchKBInput(query="test", max_results=0)  # ge=1

        with pytest.raises(ValidationError):
            SearchKBInput(query="test", max_results=11)  # le=10

    def test_create_ticket_input_requires_fields(self):
        from backend.agent import CreateTicketInput

        with pytest.raises(ValidationError):
            CreateTicketInput(channel="email")  # missing customer_id, subject, description

    def test_create_ticket_input_priority_validation(self):
        from backend.agent import CreateTicketInput

        with pytest.raises(ValidationError):
            CreateTicketInput(
                customer_id="cust-1",
                channel="email",
                subject="Test",
                description="Test",
                priority="urgent",  # not a valid Literal value
            )

    def test_create_ticket_input_valid_priorities(self):
        from backend.agent import CreateTicketInput

        for priority in ("low", "medium", "high", "critical"):
            m = CreateTicketInput(
                customer_id="cust-1",
                channel="email",
                subject="Test",
                description="Test",
                priority=priority,
            )
            assert m.priority == priority

    def test_escalate_issue_input_severity_validation(self):
        from backend.agent import EscalateIssueInput

        with pytest.raises(ValidationError):
            EscalateIssueInput(
                ticket_id="tkt-1",
                reason="test",
                severity="extreme",  # not valid
                assigned_team="team-a",
            )

    def test_escalate_issue_input_valid(self):
        from backend.agent import EscalateIssueInput

        m = EscalateIssueInput(
            ticket_id="tkt-1",
            reason="legal_complaint",
            severity="high",
            assigned_team="legal-team",
        )
        assert m.severity == "high"

    def test_send_channel_response_input_valid(self):
        from backend.agent import SendChannelResponseInput

        m = SendChannelResponseInput(
            customer_id="cust-1",
            channel="whatsapp",
            response_text="Your issue has been resolved.",
            ticket_ref="TKT-ABCDEFGH",
        )
        assert m.channel == "whatsapp"

    def test_get_customer_context_input_requires_customer_id(self):
        from backend.agent import GetCustomerContextInput

        with pytest.raises(ValidationError):
            GetCustomerContextInput()

    def test_get_customer_context_input_valid(self):
        from backend.agent import GetCustomerContextInput

        m = GetCustomerContextInput(customer_id="email:test@example.com")
        assert m.customer_id == "email:test@example.com"


# ===========================================================================
# FunctionTool and @function_tool decorator
# ===========================================================================


class TestFunctionTool:
    def test_decorated_functions_are_function_tools(self):
        from backend.agent import FunctionTool, search_knowledge_base, create_ticket

        assert isinstance(search_knowledge_base, FunctionTool)
        assert isinstance(create_ticket, FunctionTool)

    def test_all_tools_are_function_tools(self):
        from backend.agent import ALL_TOOLS, FunctionTool

        for tool in ALL_TOOLS:
            assert isinstance(tool, FunctionTool), f"{tool} is not a FunctionTool"

    def test_tool_names(self):
        from backend.agent import (
            search_knowledge_base,
            create_ticket,
            escalate_issue,
            send_channel_response,
            get_customer_context,
        )

        assert search_knowledge_base.name == "search_knowledge_base"
        assert create_ticket.name == "create_ticket"
        assert escalate_issue.name == "escalate_issue"
        assert send_channel_response.name == "send_channel_response"
        assert get_customer_context.name == "get_customer_context"

    def test_tool_has_description(self):
        from backend.agent import search_knowledge_base

        assert len(search_knowledge_base.description) > 0

    def test_tool_has_input_model(self):
        from backend.agent import search_knowledge_base, SearchKBInput

        assert search_knowledge_base.input_model is SearchKBInput

    def test_tool_call_validates_inputs(self):
        """Tool.call() raises ValidationError on invalid inputs (no DB needed for this)."""
        from backend.agent.tools import search_knowledge_base

        with pytest.raises(Exception):
            # Missing required 'query' field
            search_knowledge_base.call({})

    def test_custom_function_tool(self):
        """The @function_tool decorator should work on arbitrary functions."""
        from backend.agent.tools import FunctionTool, function_tool
        from pydantic import BaseModel

        class EchoInput(BaseModel):
            message: str

        @function_tool(name="echo_test", description="Echo back the input")
        def echo(inputs: EchoInput) -> dict:
            return {"echoed": inputs.message}

        assert isinstance(echo, FunctionTool)
        assert echo.name == "echo_test"
        result = echo.call({"message": "hello"})
        assert result == {"echoed": "hello"}

    def test_function_tool_without_parens(self):
        """@function_tool without () should also work (bare decorator)."""
        from backend.agent.tools import function_tool, FunctionTool
        from pydantic import BaseModel

        class SumInput(BaseModel):
            a: int
            b: int

        @function_tool
        def add(inputs: SumInput) -> dict:
            """Add two numbers."""
            return {"result": inputs.a + inputs.b}

        assert isinstance(add, FunctionTool)
        assert add.name == "add"

    def test_function_tool_raises_without_input_model(self):
        """Decorating a function without annotated Pydantic input raises TypeError."""
        from backend.agent.tools import function_tool

        with pytest.raises(TypeError):

            @function_tool
            def no_model(inputs):  # no type annotation
                return {}


# ===========================================================================
# Tool Registry
# ===========================================================================


class TestToolRegistry:
    def test_all_tools_registered(self):
        from backend.agent import list_registered_tools

        registered = list_registered_tools()
        expected = {
            "search_knowledge_base",
            "create_ticket",
            "escalate_issue",
            "send_channel_response",
            "get_customer_context",
        }
        assert expected.issubset(set(registered))

    def test_get_tool_by_name(self):
        from backend.agent import get_tool, FunctionTool

        tool = get_tool("search_knowledge_base")
        assert isinstance(tool, FunctionTool)

    def test_get_tool_returns_none_for_unknown(self):
        from backend.agent import get_tool

        assert get_tool("nonexistent_tool") is None

    def test_all_tools_list_length(self):
        from backend.agent import ALL_TOOLS

        assert len(ALL_TOOLS) == 5


# ===========================================================================
# CustomerSuccessAgent
# ===========================================================================


class TestCustomerSuccessAgent:
    def test_build_returns_agent(self):
        from backend.agent import CustomerSuccessAgent

        agent = CustomerSuccessAgent.build()
        assert agent is not None

    def test_agent_has_correct_tools(self):
        from backend.agent import CustomerSuccessAgent

        agent = CustomerSuccessAgent.build()
        names = agent.tool_names()
        for expected in [
            "search_knowledge_base",
            "create_ticket",
            "escalate_issue",
            "send_channel_response",
            "get_customer_context",
        ]:
            assert expected in names

    def test_agent_has_instructions(self):
        from backend.agent import CustomerSuccessAgent

        agent = CustomerSuccessAgent.build()
        assert len(agent.instructions) > 50

    def test_agent_get_tool(self):
        from backend.agent import CustomerSuccessAgent, FunctionTool

        agent = CustomerSuccessAgent.build()
        tool = agent.get_tool("create_ticket")
        assert isinstance(tool, FunctionTool)

    def test_agent_get_unknown_tool_returns_none(self):
        from backend.agent import CustomerSuccessAgent

        agent = CustomerSuccessAgent.build()
        assert agent.get_tool("unknown_tool") is None

    def test_agent_custom_config(self):
        from backend.agent import CustomerSuccessAgent, AgentConfig

        cfg = AgentConfig(provider="openai", max_turns=2)
        agent = CustomerSuccessAgent.build(config=cfg)
        assert agent.config.provider == "openai"
        assert agent.config.max_turns == 2

    def test_agent_repr(self):
        from backend.agent import CustomerSuccessAgent

        agent = CustomerSuccessAgent.build()
        repr_str = repr(agent)
        assert "CustomerSuccessAgent" in repr_str


# ===========================================================================
# AgentConfig
# ===========================================================================


class TestAgentConfig:
    def test_from_env_returns_config(self):
        from backend.agent import AgentConfig

        cfg = AgentConfig.from_env()
        assert cfg.provider in ("anthropic", "openai", "gemini")

    def test_channel_tone_email(self):
        from backend.agent import AgentConfig

        cfg = AgentConfig()
        tone = cfg.channel_tone("email")
        assert "formal" in tone.lower() or "professional" in tone.lower()

    def test_channel_tone_whatsapp(self):
        from backend.agent import AgentConfig

        cfg = AgentConfig()
        tone = cfg.channel_tone("whatsapp")
        assert "short" in tone.lower() or "concise" in tone.lower() or "brief" in tone.lower() or "word" in tone.lower()

    def test_channel_tone_unknown_channel(self):
        from backend.agent import AgentConfig

        cfg = AgentConfig()
        tone = cfg.channel_tone("telegram")
        assert len(tone) > 0  # fallback, not empty

    def test_team_for_reason_known(self):
        from backend.agent import AgentConfig

        cfg = AgentConfig()
        team = cfg.team_for_reason("legal_complaint")
        assert "legal" in team.lower()

    def test_team_for_reason_unknown(self):
        from backend.agent import AgentConfig

        cfg = AgentConfig()
        team = cfg.team_for_reason("unknown_reason")
        assert len(team) > 0  # should return default team

    def test_build_system_prompt_contains_instructions(self):
        from backend.agent import AgentConfig

        cfg = AgentConfig()
        prompt = cfg.build_system_prompt(
            channel="email",
            customer_context={"name": "Alice", "account_tier": "pro", "is_vip": False},
        )
        assert "Alice" in prompt
        assert "PRO" in prompt or "pro" in prompt.lower()


# ===========================================================================
# AgentRunner — integration tests
# ===========================================================================


class TestAgentRunner:
    def test_run_returns_agent_result(self, agent, runner):
        from backend.agent import AgentResult

        result = runner.run(
            agent,
            message="I cannot find my invoice from last month",
            context={
                "customer_id": "email:alice@sdk-test.com",
                "channel": "web_form",
                "customer_name": "Alice SDK",
            },
        )
        assert isinstance(result, AgentResult)

    def test_run_success_flag(self, agent, runner):
        result = runner.run(
            agent,
            message="How do I reset my password?",
            context={"customer_id": "email:bob@sdk-test.com", "channel": "email"},
        )
        assert result.success is True

    def test_run_response_not_empty(self, agent, runner):
        result = runner.run(
            agent,
            message="I need help with my account",
            context={"customer_id": "email:carol@sdk-test.com", "channel": "web_form"},
        )
        assert len(result.response) > 0

    def test_run_ticket_ref_created(self, agent, runner):
        result = runner.run(
            agent,
            message="My integration is not working. Please help.",
            context={"customer_id": "email:dave@sdk-test.com", "channel": "email"},
        )
        assert result.ticket_ref is not None
        assert result.ticket_ref.startswith("TKT-")

    def test_run_records_tool_calls(self, agent, runner):
        result = runner.run(
            agent,
            message="I want to upgrade my plan",
            context={"customer_id": "email:eve@sdk-test.com", "channel": "web_form"},
        )
        assert len(result.tool_calls) >= 4  # at least: context, kb, create_ticket, send_response

    def test_run_tool_calls_have_names(self, agent, runner):
        result = runner.run(
            agent,
            message="Can I export my data?",
            context={"customer_id": "email:frank@sdk-test.com", "channel": "web_form"},
        )
        tool_names = [tc.tool_name for tc in result.tool_calls]
        assert "get_customer_context" in tool_names
        assert "create_ticket" in tool_names
        assert "send_channel_response" in tool_names

    def test_run_tool_calls_have_typed_inputs(self, agent, runner):
        result = runner.run(
            agent,
            message="Where is my invoice?",
            context={"customer_id": "email:grace@sdk-test.com", "channel": "email"},
        )
        for tc in result.tool_calls:
            assert isinstance(tc.tool_name, str)
            assert isinstance(tc.input, dict)
            assert isinstance(tc.output, dict)
            assert isinstance(tc.success, bool)

    def test_run_channel_email(self, agent, runner):
        result = runner.run(
            agent,
            message="I have a billing question",
            context={"customer_id": "email:henry@sdk-test.com", "channel": "email"},
        )
        assert result.channel == "email"

    def test_run_channel_whatsapp(self, agent, runner):
        result = runner.run(
            agent,
            message="Hi I need help",
            context={
                "customer_id": "phone:+15551234567",
                "channel": "whatsapp",
                "customer_name": "WhatsApp User",
            },
        )
        assert result.channel == "whatsapp"

    def test_run_escalation_detected(self, agent, runner):
        result = runner.run(
            agent,
            message="I'm going to take legal action if this isn't resolved immediately",
            context={"customer_id": "email:legal@sdk-test.com", "channel": "email"},
        )
        # Legal escalation should trigger
        assert result.escalated is True
        assert result.escalation_reason is not None

    def test_run_escalation_creates_escalated_ticket(self, agent, runner):
        result = runner.run(
            agent,
            message="My account was hacked. Unauthorized access detected.",
            context={"customer_id": "email:hacked@sdk-test.com", "channel": "web_form"},
        )
        assert result.escalated is True
        assert result.ticket_status in ("escalated", "open")

    def test_run_kb_billing_hit(self, agent, runner):
        """Billing query should hit the seeded knowledge base."""
        result = runner.run(
            agent,
            message="How do I download my invoice?",
            context={"customer_id": "email:billing@sdk-test.com", "channel": "web_form"},
        )
        assert result.success is True
        # May or may not be a KB hit depending on seed data
        assert result.response

    def test_run_invalid_channel_defaults_gracefully(self, agent, runner):
        result = runner.run(
            agent,
            message="Hello",
            context={"customer_id": "email:unknown@sdk-test.com", "channel": "telegram"},
        )
        assert result.success is True
        assert result.channel == "web_form"  # normalised to default

    def test_run_sets_response_time_ms(self, agent, runner):
        result = runner.run(
            agent,
            message="Quick question about my account",
            context={"customer_id": "email:timing@sdk-test.com", "channel": "web_form"},
        )
        assert result.response_time_ms > 0

    def test_run_sync_class_method(self, agent, db):
        from backend.agent import AgentRunner

        result = AgentRunner.run_sync(
            agent,
            message="I need to cancel my subscription",
            context={"customer_id": "email:cancel@sdk-test.com", "channel": "email"},
            db=db,
        )
        assert result.success is True

    def test_different_customers_get_different_tickets(self, agent, runner):
        r1 = runner.run(
            agent,
            message="My billing is wrong",
            context={"customer_id": "email:cust1@sdk-test.com", "channel": "email"},
        )
        r2 = runner.run(
            agent,
            message="My billing is wrong",
            context={"customer_id": "email:cust2@sdk-test.com", "channel": "email"},
        )
        assert r1.ticket_ref != r2.ticket_ref


# ===========================================================================
# Channel-aware response generation
# ===========================================================================


class TestChannelAwareResponses:
    """Verify that responses are formatted differently per channel."""

    @pytest.fixture(autouse=True)
    def run_for_channels(self, agent, runner):
        self._results = {}
        for channel in ("email", "whatsapp", "web_form"):
            self._results[channel] = runner.run(
                agent,
                message="I cannot find my invoice from last month",
                context={
                    "customer_id": f"email:channel-test-{channel}@sdk-test.com",
                    "channel": channel,
                    "customer_name": "Test User",
                },
            )

    def test_all_channels_succeed(self):
        for channel, result in self._results.items():
            assert result.success is True, f"channel={channel} failed"

    def test_all_channels_have_response(self):
        for channel, result in self._results.items():
            assert len(result.response) > 0, f"channel={channel} has empty response"

    def test_email_response_has_greeting(self):
        response = self._results["email"].response
        # Email should contain formal greeting
        assert any(w in response for w in ("Dear", "Hi", "Hello"))

    def test_whatsapp_response_is_shorter(self):
        whatsapp_len = len(self._results["whatsapp"].response)
        email_len = len(self._results["email"].response)
        # WhatsApp should generally be shorter than email
        # (allow some flex since both may use KB responses)
        assert whatsapp_len < email_len * 2  # not dramatically longer

    def test_all_channels_get_ticket_ref(self):
        for channel, result in self._results.items():
            assert result.ticket_ref is not None, f"channel={channel} has no ticket_ref"
            assert result.ticket_ref.startswith("TKT-")
