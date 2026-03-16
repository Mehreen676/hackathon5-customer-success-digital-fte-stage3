"""
Agent Package — OpenAI Agents SDK Style Layer (Stage 3)

This package provides an Agents-SDK-style abstraction on top of the existing
Stage 3 AI workflow.  It is an additive layer — the underlying FastAPI backend
and workflow pipeline are unchanged.

Public API
──────────

Core classes::

    from backend.agent import CustomerSuccessAgent, AgentRunner, AgentConfig

    # Build the default agent
    agent = CustomerSuccessAgent.build()

    # Run with an injected database session
    runner = AgentRunner(db=session)
    result = runner.run(agent, message="I need help with my invoice", context={
        "customer_id": "email:alice@example.com",
        "channel": "email",
        "customer_name": "Alice Johnson",
    })

    print(result.ticket_ref)      # TKT-XXXXXXXX
    print(result.escalated)       # False
    print(len(result.tool_calls)) # 7 (one per pipeline step)

SDK-style shorthand (mirrors ``Runner.run_sync``)::

    result = AgentRunner.run_sync(agent, message, context, db=session)

Tools::

    from backend.agent import (
        search_knowledge_base,
        create_ticket,
        escalate_issue,
        send_channel_response,
        get_customer_context,
        ALL_TOOLS,
        FunctionTool,
        function_tool,
    )

Typed models::

    from backend.agent import (
        AgentResult,
        ToolCall,
        SearchKBInput,
        CreateTicketInput,
        EscalateIssueInput,
        SendChannelResponseInput,
        GetCustomerContextInput,
    )

Relationship to the real OpenAI Agents SDK
────────────────────────────────────────────
If the ``agents`` package is installed, you could swap this package for
the real SDK.  The main differences are:

  Real SDK                         This package
  ────────────────────────────     ────────────────────────────
  agents.Agent                 →   CustomerSuccessAgent
  agents.Runner                →   AgentRunner
  agents.function_tool         →   agent.tools.function_tool
  agents.FunctionTool          →   agent.tools.FunctionTool
  Runner.run_sync(agent, msg)  →   AgentRunner.run_sync(agent, msg, ctx, db)

The main structural difference is that our runner requires an explicit
database session (injected at construction time) because the tools perform
real database operations.  In the real SDK, tool context is typically
passed through the thread-local context mechanism.
"""

from backend.agent.config import AgentConfig, CHANNEL_TONE, ESCALATION_TEAM_MAP
from backend.agent.customer_success_agent import CustomerSuccessAgent, AgentRunner
from backend.agent.models import (
    AgentResult,
    ToolCall,
    SearchKBInput,
    SearchKBOutput,
    CreateTicketInput,
    CreateTicketOutput,
    EscalateIssueInput,
    EscalateIssueOutput,
    SendChannelResponseInput,
    SendChannelResponseOutput,
    GetCustomerContextInput,
    GetCustomerContextOutput,
)
from backend.agent.tools import (
    FunctionTool,
    function_tool,
    search_knowledge_base,
    create_ticket,
    escalate_issue,
    send_channel_response,
    get_customer_context,
    ALL_TOOLS,
    list_registered_tools,
    get_tool,
)

__all__ = [
    # Core classes
    "CustomerSuccessAgent",
    "AgentRunner",
    "AgentConfig",
    # Tool infrastructure
    "FunctionTool",
    "function_tool",
    "ALL_TOOLS",
    "list_registered_tools",
    "get_tool",
    # Tools
    "search_knowledge_base",
    "create_ticket",
    "escalate_issue",
    "send_channel_response",
    "get_customer_context",
    # Result models
    "AgentResult",
    "ToolCall",
    # Input models
    "SearchKBInput",
    "SearchKBOutput",
    "CreateTicketInput",
    "CreateTicketOutput",
    "EscalateIssueInput",
    "EscalateIssueOutput",
    "SendChannelResponseInput",
    "SendChannelResponseOutput",
    "GetCustomerContextInput",
    "GetCustomerContextOutput",
    # Config
    "CHANNEL_TONE",
    "ESCALATION_TEAM_MAP",
]
