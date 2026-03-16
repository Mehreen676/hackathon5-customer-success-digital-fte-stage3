"""
Customer Success Agent — Agents SDK Layer (Stage 3)

This module implements the Agent + Runner pattern, mirroring the
OpenAI Agents SDK architecture.

Classes
────────
CustomerSuccessAgent
    Holds the agent's identity (name, instructions), tool set, and config.
    Equivalent to ``agents.Agent`` in the real SDK.

AgentRunner
    Executes an agent against a customer message.
    Equivalent to ``agents.Runner`` in the real SDK.

Architecture
────────────
Real OpenAI Agents SDK::

    from agents import Agent, Runner, function_tool

    @function_tool
    def search_kb(query: str) -> str: ...

    agent = Agent(name="CS Agent", instructions="...", tools=[search_kb])
    result = Runner.run_sync(agent, "I need help with billing")

This implementation (no SDK dependency)::

    from agent.customer_success_agent import CustomerSuccessAgent, AgentRunner
    from agent.tools import ALL_TOOLS

    agent = CustomerSuccessAgent.build()
    runner = AgentRunner(db=session)
    result = runner.run(agent, message="I need help with billing", context={...})

Relationship to src/agents/workflow.py
────────────────────────────────────────
The existing workflow.py (Stage 3) is the production pipeline used by all
FastAPI endpoints.  This agent layer is an additive Agents-SDK-style
abstraction built on top of the same underlying tools and services.

+--------------------+          +--------------------+
|  FastAPI endpoint  |          |  AgentRunner.run() |
+--------------------+          +--------------------+
         |                               |
         ▼                               ▼
  run_agent() in                 _run_tool_loop()
  src/agents/customer_success_agent.py   |
         |                 (same MCP tools, same LLM layer)
         ▼
  process_message() in src/agents/workflow.py

Both paths call the same src/mcp/tools/* and src/llm/* code.
The key difference: the Agents SDK layer wraps every step in typed
ToolCall records and returns a structured AgentResult.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from agent.config import AgentConfig
from agent.models import (
    AgentResult,
    CreateTicketInput,
    EscalateIssueInput,
    GetCustomerContextInput,
    SearchKBInput,
    SendChannelResponseInput,
    ToolCall,
)
from agent.tools import (
    ALL_TOOLS,
    FunctionTool,
    create_ticket,
    escalate_issue,
    get_customer_context,
    search_knowledge_base,
    send_channel_response,
)

logger = logging.getLogger(__name__)

VALID_CHANNELS = {"email", "whatsapp", "web_form"}


# ===========================================================================
# CustomerSuccessAgent
# ===========================================================================


class CustomerSuccessAgent:
    """
    An agent with a name, system instructions, a set of tools, and config.

    Mirrors ``agents.Agent`` from the OpenAI Agents SDK.

    Create via the factory method::

        agent = CustomerSuccessAgent.build()

    Or with custom config::

        config = AgentConfig(provider="openai", max_turns=3)
        agent = CustomerSuccessAgent.build(config=config)
    """

    def __init__(
        self,
        name: str,
        instructions: str,
        tools: list[FunctionTool],
        config: AgentConfig,
    ) -> None:
        self.name = name
        self.instructions = instructions
        self.tools = tools
        self.config = config
        # Build a name → tool lookup for fast access
        self._tool_map: dict[str, FunctionTool] = {t.name: t for t in tools}

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def build(
        cls,
        name: str = "Nexora Customer Success Agent",
        config: Optional[AgentConfig] = None,
        tools: Optional[list[FunctionTool]] = None,
    ) -> "CustomerSuccessAgent":
        """
        Build the default CustomerSuccessAgent.

        Args:
            name:   Display name for the agent.
            config: AgentConfig instance (defaults to ``AgentConfig.from_env()``).
            tools:  Tool list override (defaults to ALL_TOOLS from agent.tools).

        Returns:
            A fully configured CustomerSuccessAgent ready to run.
        """
        cfg = config or AgentConfig.from_env()
        tool_list = tools if tools is not None else ALL_TOOLS
        return cls(
            name=name,
            instructions=cfg.instructions,
            tools=tool_list,
            config=cfg,
        )

    def get_tool(self, name: str) -> Optional[FunctionTool]:
        """Look up a tool by name."""
        return self._tool_map.get(name)

    def tool_names(self) -> list[str]:
        """Return names of all tools available to this agent."""
        return [t.name for t in self.tools]

    def __repr__(self) -> str:
        return (
            f"CustomerSuccessAgent(name={self.name!r}, "
            f"tools={self.tool_names()}, provider={self.config.provider!r})"
        )


# ===========================================================================
# AgentRunner
# ===========================================================================


class AgentRunner:
    """
    Executes a CustomerSuccessAgent against an inbound customer message.

    Mirrors ``agents.Runner`` from the OpenAI Agents SDK.

    Usage::

        runner = AgentRunner(db=session)
        result = runner.run(agent, message="I need a refund", context={
            "customer_id": "email:customer@example.com",
            "channel": "email",
            "customer_name": "Alice",
            "customer_email": "alice@example.com",
        })

    The context dict must contain at minimum:
        customer_id (str)   — external customer ID or identifier
        channel     (str)   — email | whatsapp | web_form
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public run interface
    # ------------------------------------------------------------------

    def run(
        self,
        agent: CustomerSuccessAgent,
        message: str,
        context: dict,
    ) -> AgentResult:
        """
        Run the agent against a customer message.

        Args:
            agent:   The CustomerSuccessAgent to run.
            message: Raw inbound customer message text.
            context: Runtime context dict (customer_id, channel, etc.).

        Returns:
            AgentResult with response text, ticket ref, tool call trace, etc.
        """
        start = time.monotonic()

        customer_id: str = context.get("customer_id", "unknown")
        channel: str = context.get("channel", agent.config.default_channel)
        customer_name: str = context.get("customer_name", "Valued Customer")

        if channel not in VALID_CHANNELS:
            channel = "web_form"

        tool_calls: list[ToolCall] = []

        try:
            result = self._run_pipeline(
                agent=agent,
                message=message,
                customer_id=customer_id,
                channel=channel,
                customer_name=customer_name,
                tool_calls=tool_calls,
            )
        except Exception as exc:
            logger.error(
                "AgentRunner.run failed | customer=%s | error=%s", customer_id, exc
            )
            elapsed = (time.monotonic() - start) * 1000
            return AgentResult(
                success=False,
                response=_fallback_response(channel),
                channel=channel,
                customer_id=customer_id,
                customer_name=customer_name,
                tool_calls=tool_calls,
                response_time_ms=elapsed,
                error=str(exc),
            )

        result.response_time_ms = (time.monotonic() - start) * 1000
        return result

    @classmethod
    def run_sync(
        cls,
        agent: CustomerSuccessAgent,
        message: str,
        context: dict,
        db: Session,
    ) -> AgentResult:
        """
        Class-method convenience wrapper mirroring ``Runner.run_sync()`` from
        the OpenAI Agents SDK.

        Usage::

            result = AgentRunner.run_sync(agent, message, context, db=session)
        """
        runner = cls(db=db)
        return runner.run(agent, message, context)

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def _run_pipeline(
        self,
        agent: CustomerSuccessAgent,
        message: str,
        customer_id: str,
        channel: str,
        customer_name: str,
        tool_calls: list[ToolCall],
    ) -> AgentResult:
        """
        Deterministic agent pipeline — 7 steps, each recorded as a ToolCall.

        Step 1  — get_customer_context
        Step 2  — Escalation check (escalation_engine)
        Step 3  — search_knowledge_base
        Step 4  — Generate response (KB-grounded or LLM)
        Step 5  — create_ticket (with escalation flags if needed)
        Step 6  — escalate_issue  (only if escalated)
        Step 7  — send_channel_response
        """
        config = agent.config

        # ── Step 1: Customer context ──────────────────────────────────────
        ctx_output = self._call_tool(
            agent,
            "get_customer_context",
            GetCustomerContextInput(customer_id=customer_id).model_dump(),
            tool_calls,
        )
        customer_ctx = ctx_output or {}
        effective_name = customer_ctx.get("name") or customer_name

        # ── Step 2: Escalation detection ─────────────────────────────────
        escalated, escalation_reason, escalation_severity = _check_escalation(
            message, customer_ctx
        )

        # ── Step 3: Knowledge base search ────────────────────────────────
        kb_output = self._call_tool(
            agent,
            "search_knowledge_base",
            SearchKBInput(query=message, channel=channel).model_dump(),
            tool_calls,
        )
        kb_matched = bool(kb_output.get("matched")) if kb_output else False
        kb_topic = kb_output.get("top_topic") if kb_output else None
        kb_content = kb_output.get("top_content") if kb_output else None

        # ── Step 4: Response generation ───────────────────────────────────
        system_prompt = config.build_system_prompt(channel, customer_ctx)
        ai_used = False
        ai_provider: Optional[str] = None
        tokens_used = 0
        response_text: str

        if escalated:
            response_text = _escalation_response(
                channel, effective_name, escalation_reason or "general"
            )
        elif kb_matched and kb_content:
            response_text = _format_kb_response(
                channel, effective_name, kb_content, kb_topic or ""
            )
        else:
            # LLM generation
            llm_result = _try_llm(
                system_prompt=system_prompt,
                user_prompt=message,
                channel=channel,
                customer_name=effective_name,
                kb_content=kb_content,
                config=config,
            )
            if llm_result and not llm_result.get("error"):
                response_text = llm_result["content"]
                ai_used = True
                ai_provider = llm_result.get("provider")
                tokens_used = llm_result.get("tokens_used", 0)
            else:
                response_text = _fallback_response(channel)

        # ── Step 5: Create ticket ─────────────────────────────────────────
        ticket_priority = _priority_from_escalation(escalation_severity) if escalated else "low"
        ticket_status = "escalated" if escalated else "auto-resolved"
        assigned_team = (
            config.team_for_reason(escalation_reason or "") if escalated else None
        )
        ticket_subject = _subject_from_message(message)

        ticket_input = CreateTicketInput(
            customer_id=customer_ctx.get("id") or customer_id,
            channel=channel,
            subject=ticket_subject,
            description=message,
            priority=ticket_priority,
            escalated=escalated,
            escalation_reason=escalation_reason,
            escalation_severity=escalation_severity,
            assigned_team=assigned_team,
            status=ticket_status,
        )
        ticket_output = self._call_tool(
            agent,
            "create_ticket",
            ticket_input.model_dump(),
            tool_calls,
        )
        ticket_ref = (ticket_output or {}).get("ticket_ref", "TKT-UNKNOWN")
        ticket_id = (ticket_output or {}).get("ticket_id", "")

        # ── Step 6: Escalate if needed ────────────────────────────────────
        if escalated and ticket_id:
            self._call_tool(
                agent,
                "escalate_issue",
                EscalateIssueInput(
                    ticket_id=ticket_id,
                    reason=escalation_reason or "general",
                    severity=escalation_severity or "medium",
                    assigned_team=assigned_team or "senior-support",
                ).model_dump(),
                tool_calls,
            )

        # ── Step 7: Send channel response ─────────────────────────────────
        self._call_tool(
            agent,
            "send_channel_response",
            SendChannelResponseInput(
                customer_id=customer_ctx.get("id") or customer_id,
                channel=channel,
                response_text=response_text,
                ticket_ref=ticket_ref,
            ).model_dump(),
            tool_calls,
        )

        # ── Assemble result ───────────────────────────────────────────────
        return AgentResult(
            success=True,
            response=response_text,
            channel=channel,
            customer_id=customer_id,
            customer_name=effective_name,
            intent=_infer_intent(message),
            escalated=escalated,
            escalation_reason=escalation_reason,
            escalation_severity=escalation_severity,
            ticket_ref=ticket_ref,
            ticket_status=ticket_status,
            ticket_priority=ticket_priority,
            kb_used=kb_matched,
            kb_topic=kb_topic,
            ai_used=ai_used,
            ai_provider=ai_provider,
            tokens_used=tokens_used,
            tool_calls=tool_calls,
        )

    # ------------------------------------------------------------------
    # Tool dispatch helpers
    # ------------------------------------------------------------------

    def _call_tool(
        self,
        agent: CustomerSuccessAgent,
        tool_name: str,
        inputs: dict,
        tool_calls: list[ToolCall],
    ) -> dict:
        """
        Invoke a named tool, record the ToolCall, and return the output dict.

        Never raises — errors are captured in the ToolCall record and an
        empty dict is returned so the pipeline can continue.
        """
        tool = agent.get_tool(tool_name)
        if tool is None:
            logger.warning("Tool '%s' not found on agent '%s'", tool_name, agent.name)
            tool_calls.append(
                ToolCall(
                    tool_name=tool_name,
                    input=inputs,
                    output={},
                    success=False,
                    error=f"Tool '{tool_name}' not registered on this agent",
                )
            )
            return {}

        try:
            output = tool.call(inputs, db=self._db)
            tool_calls.append(
                ToolCall(
                    tool_name=tool_name,
                    input=inputs,
                    output=output,
                    success=True,
                )
            )
            logger.debug("Tool '%s' succeeded | output keys: %s", tool_name, list(output.keys()))
            return output
        except Exception as exc:
            logger.warning("Tool '%s' raised: %s", tool_name, exc)
            tool_calls.append(
                ToolCall(
                    tool_name=tool_name,
                    input=inputs,
                    output={},
                    success=False,
                    error=str(exc),
                )
            )
            return {}


# ===========================================================================
# Private helpers
# ===========================================================================


def _check_escalation(
    message: str, customer_ctx: dict
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Delegate to the existing Stage 3 escalation engine.

    Returns:
        (escalated: bool, reason: str|None, severity: str|None)
    """
    try:
        from backend.agents.escalation_engine import detect_escalation

        result = detect_escalation(message, customer_ctx)
        if result:
            return True, result.get("reason"), result.get("severity")
    except Exception as exc:
        logger.debug("Escalation engine unavailable: %s", exc)
    return False, None, None


def _try_llm(
    system_prompt: str,
    user_prompt: str,
    channel: str,
    customer_name: str,
    kb_content: Optional[str],
    config: AgentConfig,
) -> Optional[dict]:
    """
    Attempt LLM generation via the existing src/llm layer.

    Returns a dict with 'content', 'provider', 'tokens_used', or None on failure.
    """
    try:
        from backend.llm.llm_client import LLMClient

        client = LLMClient(provider=config.provider, model=config.model)
        response = client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=config.max_tokens,
        )
        if response.error:
            return None
        return {
            "content": response.content,
            "provider": response.provider,
            "tokens_used": response.tokens_used,
            "error": None,
        }
    except Exception as exc:
        logger.debug("LLM generation failed: %s", exc)
        return None


def _format_kb_response(
    channel: str, customer_name: str, kb_content: str, kb_topic: str
) -> str:
    """Format a KB-grounded response with channel-appropriate style."""
    first_name = customer_name.split()[0] if customer_name else "there"

    if channel == "email":
        return (
            f"Dear {customer_name},\n\n"
            f"Thank you for reaching out to Nexora Support.\n\n"
            f"{kb_content}\n\n"
            f"If you have any further questions, please don't hesitate to reply.\n\n"
            f"Best regards,\nNexora Support Team"
        )
    elif channel == "whatsapp":
        short = kb_content[:200].rstrip() + ("…" if len(kb_content) > 200 else "")
        return f"Hi {first_name}! ✅\n\n{short}\n\nReply if you need anything else 🙏"
    else:
        return (
            f"Hi {customer_name},\n\n"
            f"{kb_content}\n\n"
            f"Let us know if you need further help."
        )


def _escalation_response(channel: str, customer_name: str, reason: str) -> str:
    """Return a channel-appropriate escalation acknowledgment."""
    first_name = customer_name.split()[0] if customer_name else "there"
    reason_friendly = reason.replace("_", " ").title()

    if channel == "email":
        return (
            f"Dear {customer_name},\n\n"
            f"Thank you for contacting Nexora. I understand this is a concerning "
            f"situation and I want to make sure you receive the best possible support.\n\n"
            f"I've escalated your request to our specialist team ({reason_friendly}). "
            f"A member of our team will reach out to you within 4 business hours.\n\n"
            f"Your ticket reference is included in this email for tracking.\n\n"
            f"We sincerely apologise for any inconvenience.\n\n"
            f"Best regards,\nNexora Support Team"
        )
    elif channel == "whatsapp":
        return (
            f"Hi {first_name} 🙏\n\n"
            f"I've escalated your request to our specialist team. "
            f"Someone will contact you within 4 hours. Thank you for your patience."
        )
    else:
        return (
            f"Hi {customer_name},\n\n"
            f"I've escalated your request to our specialist team. "
            f"A team member will reach out within 4 business hours.\n\n"
            f"Thank you for your patience."
        )


def _fallback_response(channel: str) -> str:
    """Rule-based fallback when KB and LLM both fail."""
    if channel == "whatsapp":
        return (
            "Hi! Thanks for reaching out to Nexora Support 🙏 "
            "We've received your message and a support agent will be in touch shortly."
        )
    return (
        "Thank you for contacting Nexora Support. "
        "We've received your message and our team will respond shortly. "
        "Please keep your ticket reference for follow-up."
    )


def _priority_from_escalation(severity: Optional[str]) -> str:
    """Map escalation severity to ticket priority."""
    return {"critical": "critical", "high": "high", "medium": "medium"}.get(
        severity or "", "high"
    )


def _subject_from_message(message: str, max_len: int = 80) -> str:
    """Derive a ticket subject from the first line of the message."""
    first_line = message.strip().split("\n")[0]
    if len(first_line) > max_len:
        return first_line[:max_len].rstrip() + "…"
    return first_line


def _infer_intent(message: str) -> str:
    """
    Lightweight keyword-based intent inference.

    Delegates to the existing escalation engine's classify_intent if available,
    otherwise falls back to simple keyword matching.
    """
    try:
        from backend.agents.escalation_engine import classify_intent

        return classify_intent(message) or "general"
    except Exception:
        pass

    msg = message.lower()
    if any(k in msg for k in ["invoice", "billing", "charge", "payment", "refund"]):
        return "billing"
    if any(k in msg for k in ["password", "login", "access", "account", "sign in"]):
        return "account"
    if any(k in msg for k in ["api", "integration", "webhook", "sdk", "connect"]):
        return "integration"
    if any(k in msg for k in ["plan", "upgrade", "downgrade", "pricing", "feature"]):
        return "plan"
    if any(k in msg for k in ["data", "export", "gdpr", "delete", "privacy"]):
        return "data"
    if any(k in msg for k in ["team", "user", "member", "permission", "admin"]):
        return "team"
    return "general"
