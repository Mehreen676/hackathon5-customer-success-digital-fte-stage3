"""
Response Generator — Nexora Customer Success Digital FTE (Stage 3).

Orchestrates the 3-tier response strategy:
  Tier 1: KB Hit       — answer directly from the knowledge base
  Tier 2: LLM Call     — generate answer via LLM when KB has no match
  Tier 3: Fallback     — polite holding message when LLM is unavailable/fails

Usage::

    from backend.llm.response_generator import ResponseGenerator

    generator = ResponseGenerator()
    result = generator.generate_response(
        customer_message="How do I add a team member?",
        customer_name="Sarah",
        channel="email",
        intent="account",
        kb_results={"matched": False, "results": []},
        customer_context={},
    )
    print(result.content)   # formatted response text
    print(result.source)    # "kb" | "llm" | "fallback"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

from .llm_client import LLMClient, LLMResponse
from .prompt_templates import PromptTemplates

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------


@dataclass
class GeneratedResponse:
    """Result returned by ResponseGenerator regardless of source."""

    content: str
    source: Literal["kb", "llm", "fallback"]
    confidence: float          # 0.0 – 1.0 estimate
    provider: str = "none"
    model: str = "none"
    tokens_used: int = 0
    latency_ms: float = 0.0
    kb_topic: Optional[str] = None


# ---------------------------------------------------------------------------
# Channel word limits (mirrors send_channel_response tool)
# ---------------------------------------------------------------------------

_WORD_LIMITS: dict[str, int] = {
    "email": 400,
    "whatsapp": 100,
    "web_form": 200,
}


# ---------------------------------------------------------------------------
# Response Generator
# ---------------------------------------------------------------------------


class ResponseGenerator:
    """
    Generates channel-appropriate support responses using a 3-tier strategy.

    Tier 1: If the KB matched, format KB content directly (no LLM cost).
    Tier 2: If KB had no match, call the LLM provider.
    Tier 3: If LLM is unavailable or raises, return a polite fallback.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self._llm: Optional[LLMClient] = llm_client  # lazy-init if None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_response(
        self,
        customer_message: str,
        customer_name: str,
        channel: str,
        intent: str,
        kb_results: dict,
        customer_context: Optional[dict] = None,
    ) -> GeneratedResponse:
        """
        Generate a response using the 3-tier strategy.

        Args:
            customer_message: Raw text from the customer.
            customer_name: Display name for personalisation.
            channel: "email" | "whatsapp" | "web_form".
            intent: Classified intent (e.g. "billing", "account").
            kb_results: Dict returned by the search_kb MCP tool.
                        Expected keys: matched (bool), results (list).
            customer_context: Optional dict from get_customer_context tool.

        Returns:
            GeneratedResponse with content, source, and metadata.
        """
        customer_context = customer_context or {}

        # ------------------------------------------------------------------
        # Tier 1: KB Hit
        # ------------------------------------------------------------------
        if kb_results.get("matched") and kb_results.get("results"):
            return self._from_kb(kb_results, channel, customer_name)

        # ------------------------------------------------------------------
        # Tier 2: LLM Generation
        # ------------------------------------------------------------------
        try:
            return self._from_llm(
                customer_message=customer_message,
                customer_name=customer_name,
                channel=channel,
                intent=intent,
                kb_results=kb_results,
                customer_context=customer_context,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM generation failed, using fallback: %s", exc)

        # ------------------------------------------------------------------
        # Tier 3: Fallback
        # ------------------------------------------------------------------
        return self._fallback(customer_name, channel)

    # ------------------------------------------------------------------
    # Tier 1 — KB formatter
    # ------------------------------------------------------------------

    def _from_kb(
        self,
        kb_results: dict,
        channel: str,
        customer_name: str,
    ) -> GeneratedResponse:
        """Format KB results into a channel-appropriate response."""
        results = kb_results.get("results", [])
        top = results[0] if results else {}
        topic = top.get("topic", "general")
        content_raw = top.get("content", "")

        formatted = self.format_kb_response(
            kb_results=results,
            channel=channel,
            customer_name=customer_name,
        )

        logger.info("KB HIT | topic=%s | channel=%s", topic, channel)
        return GeneratedResponse(
            content=formatted,
            source="kb",
            confidence=min(1.0, top.get("score", 0.8) / 10 + 0.5) if top.get("score") else 0.9,
            kb_topic=topic,
        )

    def format_kb_response(
        self,
        kb_results: list,
        channel: str,
        customer_name: str,
    ) -> str:
        """
        Format a list of KB result dicts into a channel-ready string.

        Args:
            kb_results: List of dicts with 'topic' and 'content' keys.
            channel: Target channel for tone/length adjustment.
            customer_name: Customer display name.

        Returns:
            Formatted response string.
        """
        if not kb_results:
            return self._fallback(customer_name, channel).content

        first_name = customer_name.split()[0] if customer_name else "there"
        content = kb_results[0].get("content", "")

        if channel == "whatsapp":
            # Trim to ~80 words for WhatsApp
            words = content.split()
            if len(words) > 80:
                content = " ".join(words[:80]) + "…"
            return f"Hi {first_name}! 👋\n\n{content}\n\nLet me know if you need anything else! 😊"

        if channel == "email":
            return (
                f"Dear {customer_name},\n\n"
                f"Thank you for reaching out to Nexora Support.\n\n"
                f"{content}\n\n"
                "Please don't hesitate to reply if you have any further questions.\n\n"
                "Best regards,\nNexora Customer Success Team\nsupport@nexora.io"
            )

        # web_form / default
        return (
            f"Hi {first_name},\n\n"
            f"Thanks for contacting us! Here's the information you need:\n\n"
            f"{content}\n\n"
            "If this doesn't fully resolve your issue, please reply to this message "
            "and we'll follow up shortly.\n\nNexora Support Team"
        )

    # ------------------------------------------------------------------
    # Tier 2 — LLM generation
    # ------------------------------------------------------------------

    def _from_llm(
        self,
        customer_message: str,
        customer_name: str,
        channel: str,
        intent: str,
        kb_results: dict,
        customer_context: dict,
    ) -> GeneratedResponse:
        """Call the LLM and return a GeneratedResponse."""
        client = self._get_llm_client()

        if not client.is_configured():
            raise RuntimeError(
                f"LLM provider '{client.provider}' has no API key configured. "
                "Set ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY."
            )

        system_prompt = PromptTemplates.system_prompt(channel=channel)
        user_prompt = PromptTemplates.no_kb_response_prompt(
            customer_name=customer_name,
            channel=channel,
            intent=intent,
            customer_context=customer_context,
        )
        # Append the actual customer message for full context
        user_prompt = (
            f"{user_prompt}\n\n"
            f"CUSTOMER MESSAGE:\n{customer_message}"
        )

        # Add ticket history if available
        recent_tickets = customer_context.get("recent_tickets", [])
        if recent_tickets:
            ticket_ctx = PromptTemplates.ticket_context_prompt(recent_tickets)
            user_prompt = f"{ticket_ctx}\n\n{user_prompt}"

        llm_response: LLMResponse = client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=_WORD_LIMITS.get(channel, 300) * 6,  # ~6 tokens per word
        )

        if llm_response.error:
            raise RuntimeError(llm_response.error)

        logger.info(
            "LLM RESPONSE | provider=%s | model=%s | tokens=%d | %.1fms",
            client.provider, client.model, llm_response.tokens_used, llm_response.latency_ms,
        )

        return GeneratedResponse(
            content=llm_response.content,
            source="llm",
            confidence=0.75,
            provider=client.provider,
            model=client.model,
            tokens_used=llm_response.tokens_used,
            latency_ms=llm_response.latency_ms,
        )

    # ------------------------------------------------------------------
    # Tier 3 — Fallback
    # ------------------------------------------------------------------

    def _fallback(self, customer_name: str, channel: str) -> GeneratedResponse:
        """Return a polite holding message when both KB and LLM are unavailable."""
        first_name = customer_name.split()[0] if customer_name else "there"

        if channel == "whatsapp":
            content = (
                f"Hi {first_name}! 👋 Thanks for reaching out.\n"
                "I've logged your query and a specialist will reply shortly. 😊"
            )
        elif channel == "email":
            content = (
                f"Dear {customer_name},\n\n"
                "Thank you for contacting Nexora Support. I've received your message "
                "and logged your query. A specialist from our Customer Success team "
                "will provide a detailed response within 24 hours.\n\n"
                "Best regards,\nNexora Customer Success Team"
            )
        else:
            content = (
                f"Hi {first_name},\n\n"
                "Thanks for contacting Nexora Support. We've received your query and "
                "a team member will follow up with a full response shortly.\n\n"
                "Nexora Support Team"
            )

        logger.info("FALLBACK RESPONSE | channel=%s", channel)
        return GeneratedResponse(
            content=content,
            source="fallback",
            confidence=0.3,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_llm_client(self) -> LLMClient:
        """Lazily initialise the LLM client."""
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm
