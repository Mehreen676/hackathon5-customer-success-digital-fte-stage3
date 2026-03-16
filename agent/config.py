"""
Agent Configuration — Agents SDK Layer (Stage 3)

Centralises all configuration for the CustomerSuccessAgent:
  - LLM provider / model selection
  - Max turn budget and token caps
  - Channel-aware tone instructions injected into the system prompt
  - Team routing table for escalations

Design note
────────────
Configuration is intentionally separated from the agent/runner code so it
can be overridden in tests, loaded from environment variables, or replaced
with a different config source (YAML, database, feature flags) without
touching the agent logic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Channel tone and format definitions
# ---------------------------------------------------------------------------

#: Concise tone description injected into the system prompt per channel.
CHANNEL_TONE: dict[str, str] = {
    "email": (
        "Adopt a formal, professional tone. Use a proper greeting and sign-off. "
        "Structure the reply with clear paragraphs. Aim for 150–300 words."
    ),
    "whatsapp": (
        "Keep the response short, friendly, and conversational. "
        "Avoid long paragraphs — use 2–3 short sentences per point. "
        "A light emoji (e.g. ✅ 🙏) is appropriate. Max 120 words."
    ),
    "web_form": (
        "Use a balanced, clear tone. Markdown formatting is supported. "
        "Use bullet points or numbered lists where helpful. 100–250 words."
    ),
}

#: Fallback tone for unknown channels.
DEFAULT_CHANNEL_TONE: str = CHANNEL_TONE["web_form"]

# ---------------------------------------------------------------------------
# Escalation team routing
# ---------------------------------------------------------------------------

#: Maps escalation reason codes → responsible team names.
ESCALATION_TEAM_MAP: dict[str, str] = {
    "legal_complaint": "legal-team",
    "security_issue": "security-team",
    "refund_request": "billing-team",
    "pricing_negotiation": "account-management",
    "angry_customer": "senior-support",
    "vip_complaint": "vip-success-team",
    "data_request": "compliance-team",
}

#: Default team when reason code has no explicit mapping.
DEFAULT_ESCALATION_TEAM: str = "senior-support"

# ---------------------------------------------------------------------------
# Agent instructions (system prompt)
# ---------------------------------------------------------------------------

BASE_INSTRUCTIONS: str = """
You are Nexora's AI Customer Success Agent — a knowledgeable, empathetic support specialist.

Your goal is to resolve customer issues efficiently and accurately using the tools available to you.

## Tool Usage Protocol

1. ALWAYS call get_customer_context first to understand who you are helping.
2. ALWAYS call search_knowledge_base to look for a relevant support article.
3. If the knowledge base has a match, base your response on it.
4. If no KB match, generate a helpful response using your training knowledge.
5. ALWAYS call create_ticket to log every interaction.
6. Call escalate_issue when the message contains legal threats, security concerns,
   refund demands, or the customer is clearly very angry.
7. ALWAYS call send_channel_response as the final step to deliver your answer.

## Escalation Guidelines

Escalate immediately if you detect:
  - Legal threats ("lawsuit", "attorney", "legal action")
  - Security concerns ("hacked", "data breach", "unauthorized")
  - Refund requests ("refund", "money back", "reimburse")
  - Angry/frustrated customers using strong negative language
  - VIP or Enterprise customers with any active complaint

## Response Quality

- Be warm and human — acknowledge the customer's frustration before solving.
- Be specific — reference the KB article or the exact feature they asked about.
- Be concise — respect the customer's time.
- Match the channel tone precisely (see channel-specific instructions below).
"""

# ---------------------------------------------------------------------------
# AgentConfig dataclass
# ---------------------------------------------------------------------------


@dataclass
class AgentConfig:
    """
    Full configuration for a CustomerSuccessAgent instance.

    All fields have sensible defaults that respect environment variables,
    so the agent works out-of-the-box in development.
    """

    # LLM settings
    provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "anthropic")
    )
    model: Optional[str] = field(
        default_factory=lambda: os.getenv("LLM_MODEL") or None
    )
    max_tokens: int = 1024
    temperature: float = 0.3

    # Runner settings
    max_turns: int = 5
    """
    Maximum number of tool-call + generation cycles per run.
    Guards against infinite loops in the agent loop.
    """

    # Channel
    default_channel: str = "web_form"

    # Prompt
    instructions: str = BASE_INSTRUCTIONS

    # Routing
    escalation_team_map: dict[str, str] = field(
        default_factory=lambda: ESCALATION_TEAM_MAP.copy()
    )

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """
        Build an AgentConfig from environment variables.

        Respects:
            LLM_PROVIDER   — anthropic | openai | gemini
            LLM_MODEL      — model name override
        """
        return cls(
            provider=os.getenv("LLM_PROVIDER", "anthropic"),
            model=os.getenv("LLM_MODEL") or None,
        )

    def channel_tone(self, channel: str) -> str:
        """Return the tone instruction string for the given channel."""
        return CHANNEL_TONE.get(channel, DEFAULT_CHANNEL_TONE)

    def team_for_reason(self, reason: str) -> str:
        """Return the escalation team for a given reason code."""
        return self.escalation_team_map.get(reason, DEFAULT_ESCALATION_TEAM)

    def build_system_prompt(self, channel: str, customer_context: dict) -> str:
        """
        Compose the full system prompt for an agent run.

        Combines:
          1. Base instructions
          2. Channel-specific tone
          3. Customer context summary
        """
        tone = self.channel_tone(channel)
        name = customer_context.get("name", "the customer")
        tier = customer_context.get("account_tier", "starter")
        is_vip = customer_context.get("is_vip", False)
        ticket_count = customer_context.get("ticket_count", 0)

        context_summary = (
            f"Customer: {name} | Tier: {tier.upper()}"
            + (" | ⭐ VIP ACCOUNT" if is_vip else "")
            + f" | Previous tickets: {ticket_count}"
        )

        return (
            f"{self.instructions}\n\n"
            f"## Channel Tone\n{tone}\n\n"
            f"## Customer Context\n{context_summary}"
        )
