"""
Agent Models — Typed Pydantic models for the Agents SDK layer (Stage 3)

Every tool call has a strictly typed input model and a structured output model.
This mirrors the OpenAI Agents SDK pattern where tool inputs are validated
by Pydantic before the tool function is invoked.

Architecture note
─────────────────
These models are intentionally separate from the HTTP-layer schemas in
src/schemas/.  They represent the internal tool contract, not the public API
contract.  This keeps the agent layer independently testable and reusable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ===========================================================================
# Tool Input Models
# ===========================================================================


class SearchKBInput(BaseModel):
    """Input for the search_knowledge_base tool."""

    query: str = Field(
        ...,
        min_length=1,
        description="Customer message or question to search in the knowledge base.",
    )
    channel: str = Field(
        default="web_form",
        description="Originating channel: email | whatsapp | web_form",
    )
    max_results: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of knowledge base results to return.",
    )


class CreateTicketInput(BaseModel):
    """Input for the create_ticket tool."""

    customer_id: str = Field(
        ...,
        description="Internal customer UUID (from the database) or external_id.",
    )
    channel: str = Field(
        ...,
        description="Channel: email | whatsapp | web_form",
    )
    subject: str = Field(
        ...,
        min_length=1,
        description="Short subject line for the ticket.",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Full description of the customer issue.",
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        default="low",
        description="Ticket priority level.",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional conversation thread ID to link the ticket.",
    )
    escalated: bool = Field(
        default=False,
        description="Whether the ticket should immediately be in escalated state.",
    )
    escalation_reason: Optional[str] = Field(
        default=None,
        description="Reason code for escalation, e.g. 'legal_complaint'.",
    )
    escalation_severity: Optional[str] = Field(
        default=None,
        description="Severity level of the escalation.",
    )
    assigned_team: Optional[str] = Field(
        default=None,
        description="Team to assign the ticket to, e.g. 'billing-team'.",
    )


class EscalateIssueInput(BaseModel):
    """Input for the escalate_issue tool."""

    ticket_id: str = Field(
        ...,
        description="Internal ticket UUID to escalate.",
    )
    reason: str = Field(
        ...,
        description="Human-readable escalation reason, e.g. 'legal_complaint'.",
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Escalation severity level.",
    )
    assigned_team: str = Field(
        ...,
        description="Team to escalate to, e.g. 'legal-team' or 'billing-team'.",
    )


class SendChannelResponseInput(BaseModel):
    """Input for the send_channel_response tool."""

    customer_id: str = Field(
        ...,
        description="Internal customer UUID.",
    )
    channel: str = Field(
        ...,
        description="Channel to send through: email | whatsapp | web_form",
    )
    response_text: str = Field(
        ...,
        min_length=1,
        description="The final response text to deliver to the customer.",
    )
    ticket_ref: str = Field(
        ...,
        description="Ticket reference to include in the response (e.g. TKT-XXXXXXXX).",
    )


class GetCustomerContextInput(BaseModel):
    """Input for the get_customer_context tool."""

    customer_id: str = Field(
        ...,
        description="Customer external_id or internal UUID.",
    )


# ===========================================================================
# Tool Output Models
# ===========================================================================


class SearchKBOutput(BaseModel):
    """Output from the search_knowledge_base tool."""

    matched: bool
    results: list[dict] = Field(default_factory=list)
    top_topic: Optional[str] = None
    top_content: Optional[str] = None
    source: str = "database"


class CreateTicketOutput(BaseModel):
    """Output from the create_ticket tool."""

    ticket_id: str
    ticket_ref: str
    status: str
    priority: str
    escalated: bool = False
    channel: str = ""
    created_at: Optional[str] = None


class EscalateIssueOutput(BaseModel):
    """Output from the escalate_issue tool."""

    ticket_ref: str
    escalated: bool
    assigned_team: str
    severity: str


class SendChannelResponseOutput(BaseModel):
    """Output from the send_channel_response tool."""

    delivered: bool
    channel: str
    ticket_ref: str
    mode: str = "simulated"


class GetCustomerContextOutput(BaseModel):
    """Output from the get_customer_context tool."""

    customer_id: str
    name: str = "Valued Customer"
    account_tier: str = "starter"
    is_vip: bool = False
    recent_tickets: list[dict] = Field(default_factory=list)
    ticket_count: int = 0
    found: bool = False


# ===========================================================================
# Agent Run Models
# ===========================================================================


class ToolCall(BaseModel):
    """
    Record of a single tool invocation during an agent run.

    Stored in AgentResult.tool_calls so the caller can inspect
    exactly which tools were called and with what inputs/outputs.
    """

    tool_name: str
    input: dict[str, Any]
    output: dict[str, Any]
    success: bool
    error: Optional[str] = None


class AgentResult(BaseModel):
    """
    Final result returned by AgentRunner.run().

    This is the agent-layer equivalent of the workflow.py return dict,
    but strictly typed and carrying the full tool call trace.
    """

    success: bool
    response: str
    channel: str
    customer_id: str
    customer_name: str = "Valued Customer"
    intent: Optional[str] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None
    escalation_severity: Optional[str] = None
    ticket_ref: Optional[str] = None
    ticket_status: Optional[str] = None
    ticket_priority: Optional[str] = None
    kb_used: bool = False
    kb_topic: Optional[str] = None
    ai_used: bool = False
    ai_provider: Optional[str] = None
    tokens_used: int = 0
    response_time_ms: float = 0.0
    tool_calls: list[ToolCall] = Field(default_factory=list)
    error: Optional[str] = None
