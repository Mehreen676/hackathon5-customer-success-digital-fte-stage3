"""
Agent Tools — @function_tool decorated tool implementations (Stage 3)

This module provides the five core tools available to the CustomerSuccessAgent.
Each tool is decorated with @function_tool which:
  1. Validates inputs using the associated Pydantic model
  2. Registers the tool in the module-level _TOOL_REGISTRY dict
  3. Returns a FunctionTool instance (not the raw function)

This mirrors the OpenAI Agents SDK pattern where:
  - @function_tool wraps Python functions as FunctionTool objects
  - Inputs are strictly typed via Pydantic BaseModel subclasses
  - Tools are attached to Agent instances and invoked by the Runner

Relationship to existing code
───────────────────────────────
These tools are thin, typed wrappers around the existing MCP tools in
src/mcp/tools/.  All business logic lives in the MCP layer — this file
adds the Pydantic validation layer and the FunctionTool abstraction.

If the real OpenAI Agents SDK (agents package) is installed, the FunctionTool
class here can be replaced by agents.FunctionTool and the decorator by
agents.function_tool.  The tool function signatures stay the same.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.agent.models import (
    CreateTicketInput,
    CreateTicketOutput,
    EscalateIssueInput,
    EscalateIssueOutput,
    GetCustomerContextInput,
    GetCustomerContextOutput,
    SearchKBInput,
    SearchKBOutput,
    SendChannelResponseInput,
    SendChannelResponseOutput,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# FunctionTool  — core abstraction mirroring OpenAI Agents SDK
# ===========================================================================


class FunctionTool:
    """
    A typed, callable tool that can be attached to an Agent.

    Mirrors the OpenAI Agents SDK ``FunctionTool`` class.

    Attributes:
        name:         Tool name used in tool call records and logging.
        description:  One-line description used in the system prompt.
        input_model:  Pydantic model class for input validation.
        fn:           The underlying Python function.

    Usage::

        result_dict = tool.call({"query": "billing invoice"}, db=session)
    """

    def __init__(
        self,
        fn: Callable,
        name: str,
        description: str,
        input_model: Type[BaseModel],
    ) -> None:
        self.fn = fn
        self.name = name
        self.description = description
        self.input_model = input_model
        # Preserve function metadata for introspection
        functools.update_wrapper(self, fn)

    def call(self, inputs: dict, db: Optional[Session] = None) -> dict:
        """
        Validate inputs with the Pydantic model, then invoke the tool.

        Args:
            inputs: Raw dict of tool arguments.
            db:     SQLAlchemy session injected by the runner.

        Returns:
            A plain dict (serialised from the output model).

        Raises:
            pydantic.ValidationError: If inputs fail schema validation.
        """
        validated: BaseModel = self.input_model(**inputs)
        if db is not None:
            result = self.fn(validated, db)
        else:
            result = self.fn(validated)

        if isinstance(result, BaseModel):
            return result.model_dump()
        return result

    def __repr__(self) -> str:
        return f"FunctionTool(name={self.name!r}, input={self.input_model.__name__})"


# ===========================================================================
# @function_tool decorator
# ===========================================================================


def function_tool(
    fn: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    input_model: Optional[Type[BaseModel]] = None,
) -> Any:
    """
    Decorator that wraps a Python function as a FunctionTool.

    Mirrors ``agents.function_tool`` from the OpenAI Agents SDK.

    Can be used two ways::

        # Simple — infers name, description and input_model automatically
        @function_tool
        def search_knowledge_base(inputs: SearchKBInput, db: Session) -> SearchKBOutput:
            ...

        # Explicit — override any field
        @function_tool(name="kb_search", description="Search articles")
        def search_knowledge_base(inputs: SearchKBInput, db: Session) -> SearchKBOutput:
            ...

    Input model inference
    ─────────────────────
    The decorator infers the Pydantic model from the first annotated parameter.
    If the first parameter is not annotated with a BaseModel subclass, you must
    pass ``input_model=`` explicitly.
    """

    def decorator(func: Callable) -> FunctionTool:
        tool_name = name or func.__name__
        raw_doc = (func.__doc__ or "").strip()
        tool_description = description or (raw_doc.split("\n")[0] if raw_doc else tool_name)

        # Infer input_model from the first annotated parameter
        hints = {
            k: v
            for k, v in (func.__annotations__ or {}).items()
            if k != "return"
        }
        resolved_model = input_model
        if resolved_model is None:
            for _param_name, annotation in hints.items():
                if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                    resolved_model = annotation
                    break

        if resolved_model is None:
            raise TypeError(
                f"@function_tool '{tool_name}': could not determine input_model. "
                "Annotate the first parameter with a Pydantic BaseModel subclass "
                "or pass input_model= explicitly."
            )

        tool = FunctionTool(
            fn=func,
            name=tool_name,
            description=tool_description,
            input_model=resolved_model,
        )
        # Register in module-level registry immediately
        _register(tool)
        logger.debug("Registered FunctionTool: %s", tool_name)
        return tool

    # Support both @function_tool and @function_tool(...)
    if fn is not None:
        return decorator(fn)
    return decorator


# ===========================================================================
# Tool Registry
# ===========================================================================

_TOOL_REGISTRY: dict[str, FunctionTool] = {}


def _register(tool: FunctionTool) -> None:
    _TOOL_REGISTRY[tool.name] = tool


def get_tool(name: str) -> Optional[FunctionTool]:
    """Retrieve a registered FunctionTool by name."""
    return _TOOL_REGISTRY.get(name)


def list_registered_tools() -> list[str]:
    """Return names of all registered FunctionTools in this module."""
    return sorted(_TOOL_REGISTRY.keys())


# ===========================================================================
# Tool Implementations
# ===========================================================================


@function_tool
def search_knowledge_base(inputs: SearchKBInput, db: Session) -> SearchKBOutput:
    """Search the Nexora knowledge base for articles matching a customer query."""
    try:
        from backend.mcp.tool_registry import call_tool

        result = call_tool("search_kb", query=inputs.query, db=db)
        matched = bool(result.get("matched"))
        results = result.get("results", [])
        top = results[0] if results else {}

        return SearchKBOutput(
            matched=matched,
            results=results[: inputs.max_results],
            top_topic=top.get("topic"),
            top_content=top.get("content"),
            source=result.get("source", "database"),
        )
    except Exception as exc:
        logger.warning("search_knowledge_base: MCP call failed → %s", exc)
        return SearchKBOutput(matched=False, results=[], source="error")


@function_tool
def create_ticket(inputs: CreateTicketInput, db: Session) -> CreateTicketOutput:
    """Create a support ticket in the database and return the ticket reference."""
    try:
        from backend.mcp.tool_registry import call_tool

        result = call_tool(
            "create_ticket",
            customer_id=inputs.customer_id,
            channel=inputs.channel,
            subject=inputs.subject,
            description=inputs.description,
            priority=inputs.priority,
            conversation_id=inputs.conversation_id,
            escalated=inputs.escalated,
            escalation_reason=inputs.escalation_reason,
            escalation_severity=inputs.escalation_severity,
            assigned_team=inputs.assigned_team,
            db=db,
        )
        return CreateTicketOutput(
            ticket_id=result.get("ticket_id", ""),
            ticket_ref=result.get("ticket_ref", ""),
            status=result.get("status", "open"),
            priority=result.get("priority", inputs.priority),
            escalated=result.get("escalated", inputs.escalated),
            channel=result.get("channel", inputs.channel),
            created_at=result.get("created_at"),
        )
    except Exception as exc:
        logger.warning("create_ticket: MCP call failed → %s", exc)
        return CreateTicketOutput(
            ticket_id="",
            ticket_ref="TKT-ERROR",
            status="error",
            priority=inputs.priority,
        )


@function_tool
def escalate_issue(inputs: EscalateIssueInput, db: Session) -> EscalateIssueOutput:
    """Escalate an open support ticket to a human specialist team."""
    try:
        from backend.mcp.tool_registry import call_tool

        result = call_tool(
            "escalate_issue",
            ticket_id=inputs.ticket_id,
            reason=inputs.reason,
            severity=inputs.severity,
            assigned_team=inputs.assigned_team,
            db=db,
        )
        return EscalateIssueOutput(
            ticket_ref=result.get("ticket_ref", ""),
            escalated=result.get("escalated", True),
            assigned_team=result.get("assigned_team", inputs.assigned_team),
            severity=result.get("severity", inputs.severity),
        )
    except Exception as exc:
        logger.warning("escalate_issue: MCP call failed → %s", exc)
        return EscalateIssueOutput(
            ticket_ref="",
            escalated=False,
            assigned_team=inputs.assigned_team,
            severity=inputs.severity,
        )


@function_tool
def send_channel_response(
    inputs: SendChannelResponseInput, db: Session
) -> SendChannelResponseOutput:
    """Deliver the final agent response to the customer through their channel."""
    try:
        from backend.mcp.tool_registry import call_tool

        result = call_tool(
            "send_channel_response",
            customer_id=inputs.customer_id,
            channel=inputs.channel,
            response_text=inputs.response_text,
            ticket_ref=inputs.ticket_ref,
            db=db,
        )
        return SendChannelResponseOutput(
            delivered=result.get("delivered", True),
            channel=inputs.channel,
            ticket_ref=inputs.ticket_ref,
            mode=result.get("mode", "simulated"),
        )
    except Exception as exc:
        logger.warning("send_channel_response: MCP call failed → %s", exc)
        return SendChannelResponseOutput(
            delivered=False,
            channel=inputs.channel,
            ticket_ref=inputs.ticket_ref,
            mode="error",
        )


@function_tool
def get_customer_context(
    inputs: GetCustomerContextInput, db: Session
) -> GetCustomerContextOutput:
    """Retrieve customer profile, account tier, VIP status, and recent ticket history."""
    try:
        from backend.mcp.tool_registry import call_tool

        result = call_tool("get_customer_context", customer_id=inputs.customer_id, db=db)
        return GetCustomerContextOutput(
            customer_id=inputs.customer_id,
            name=result.get("name", "Valued Customer"),
            account_tier=result.get("account_tier", "starter"),
            is_vip=result.get("is_vip", False),
            recent_tickets=result.get("recent_tickets", []),
            ticket_count=result.get("ticket_count", 0),
            found=result.get("found", False),
        )
    except Exception as exc:
        logger.warning("get_customer_context: MCP call failed → %s", exc)
        return GetCustomerContextOutput(customer_id=inputs.customer_id)


# ---------------------------------------------------------------------------
# Convenience: all tools as a list (used when building the default agent)
# ---------------------------------------------------------------------------

ALL_TOOLS: list[FunctionTool] = [
    search_knowledge_base,
    create_ticket,
    escalate_issue,
    send_channel_response,
    get_customer_context,
]
