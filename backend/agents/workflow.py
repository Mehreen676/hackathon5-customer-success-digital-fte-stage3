"""
Agent Workflow — Customer Success Digital FTE (Stage 3)

Extends the Stage 2 9-step pipeline with AI reasoning (Step 7a) and analytics
tracking. The full 10-step pipeline is:

    1.  Validate channel
    2.  Identify / create customer
    3.  Get or create conversation thread
    4.  Retrieve customer context  (MCP: get_customer_context)
    5.  Classify intent
    6.  Evaluate escalation rules  (escalation_engine)
    7.  If escalated → create ticket + escalate_issue  (ESCALATION PATH)
    7a. If not escalated → search KB
    7b. If KB miss → call LLM response generator  (NEW IN STAGE 3)
    8.  Create ticket
    9.  Format and send channel response  (MCP: send_channel_response)
    10. Store conversation messages + record analytics metrics

Stage 2 behaviour is fully preserved. The AI layer is additive — it only
activates when the KB has no match and gracefully degrades if the LLM is
unavailable.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from backend.agents.escalation_engine import classify_intent, detect_escalation
from backend.mcp.tool_registry import call_tool

logger = logging.getLogger(__name__)

VALID_CHANNELS = {"email", "whatsapp", "web_form"}


def process_message(
    customer_id: str,
    channel: str,
    content: str,
    db: Session,
    customer_name: str = "",
    customer_email: Optional[str] = None,
) -> dict:
    """
    Main Stage 3 agent entry point.

    Processes one inbound customer message through the full AI-augmented
    pipeline. Backward-compatible with Stage 2 callers — the return dict is
    a strict superset of the Stage 2 response dict.

    Args:
        customer_id: External customer ID (e.g. "CUST-001") or identifier.
        channel: Originating channel — email | whatsapp | web_form.
        content: Raw customer message text.
        db: SQLAlchemy database session.
        customer_name: Optional display name for new customers.
        customer_email: Optional email for new customers.

    Returns:
        dict with keys:
            success, escalated, escalation_reason, escalation_severity,
            ticket, response, channel, customer, intent,
            kb_used, kb_topic,
            ai_used, ai_provider, ai_model, tokens_used,
            response_time_ms, conversation_id
    """
    start_time = time.monotonic()

    # ------------------------------------------------------------------
    # Step 1: Validate channel
    # ------------------------------------------------------------------
    if channel not in VALID_CHANNELS:
        return {
            "success": False,
            "error": f"Unknown channel '{channel}'. Supported: {sorted(VALID_CHANNELS)}",
        }

    # ------------------------------------------------------------------
    # Step 2: Identify or create customer
    # ------------------------------------------------------------------
    from backend.database import crud  # late import avoids circular deps at module level

    customer = crud.get_or_create_customer(
        db=db,
        external_id=customer_id,
        name=customer_name or "Valued Customer",
        email=customer_email,
    )

    # ------------------------------------------------------------------
    # Step 3: Get or create conversation thread
    # ------------------------------------------------------------------
    conversation = crud.get_or_create_conversation(db, customer.id, channel)

    # ------------------------------------------------------------------
    # Step 4: Retrieve customer context via MCP tool
    # ------------------------------------------------------------------
    customer_ctx = call_tool("get_customer_context", customer_id=customer.id, db=db)
    display_name = customer_ctx.get("name", "Valued Customer")

    # ------------------------------------------------------------------
    # Step 5: Classify intent
    # ------------------------------------------------------------------
    intent = classify_intent(content)

    # ------------------------------------------------------------------
    # Step 6: Escalation detection
    # ------------------------------------------------------------------
    escalation = detect_escalation(content, customer_ctx)

    if escalation:
        # ================================================================
        # ESCALATION PATH
        # ================================================================

        ticket_data = call_tool(
            "create_ticket",
            customer_id=customer.id,
            channel=channel,
            subject=f"[{intent.upper()}] {content[:80]}",
            description=content,
            priority=escalation["severity"],
            status="escalated",
            conversation_id=conversation.id,
            escalated=True,
            escalation_reason=escalation["reason"],
            escalation_severity=escalation["severity"],
            db=db,
        )

        escalation_result = call_tool(
            "escalate_issue",
            ticket_id=ticket_data["ticket_id"],
            ticket_ref=ticket_data["ticket_ref"],
            reason=escalation["reason"],
            severity=escalation["severity"],
            channel=channel,
            customer_name=display_name,
            db=db,
        )

        response_text = escalation_result["holding_response"]

        crud.escalate_conversation(db, conversation.id)
        crud.create_message(db, conversation.id, "customer", content, channel)
        crud.create_message(db, conversation.id, "agent", response_text, channel)

        elapsed_ms = (time.monotonic() - start_time) * 1000

        crud.create_metric(
            db=db,
            channel=channel,
            ticket_id=ticket_data["ticket_id"],
            conversation_id=conversation.id,
            intent=intent,
            escalated=True,
            escalation_reason=escalation["reason"],
            kb_used=False,
            processing_time_ms=elapsed_ms,
        )

        _record_analytics(
            interaction_id=str(conversation.id),
            channel=channel,
            intent=intent,
            response_source="escalation",
            response_time_ms=elapsed_ms,
            escalated=True,
            kb_used=False,
            ai_used=False,
            ticket_created=True,
        )

        logger.info(
            "ESCALATED | customer=%s | reason=%s | severity=%s | ticket=%s",
            customer_id, escalation["reason"], escalation["severity"], ticket_data["ticket_ref"],
        )

        return {
            "success": True,
            "escalated": True,
            "escalation_reason": escalation["reason"],
            "escalation_severity": escalation["severity"],
            "ticket": ticket_data,
            "response": response_text,
            "channel": channel,
            "customer": display_name,
            "intent": intent,
            "kb_used": False,
            "kb_topic": None,
            "ai_used": False,
            "ai_provider": None,
            "ai_model": None,
            "tokens_used": 0,
            "response_time_ms": round(elapsed_ms, 2),
            "conversation_id": conversation.id,
        }

    # ====================================================================
    # NON-ESCALATION PATH
    # ====================================================================

    # ------------------------------------------------------------------
    # Step 7a: Knowledge base search
    # ------------------------------------------------------------------
    kb_result = call_tool("search_kb", query=content, db=db)

    ai_used = False
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    tokens_used = 0
    kb_topic: Optional[str] = None
    response_body: str

    if kb_result["matched"]:
        # KB Hit — use article content directly
        top_match = kb_result["results"][0]
        response_body = top_match["content"]
        kb_topic = top_match["topic"]
        ticket_status = "auto-resolved"
        response_source = "kb"

    else:
        # KB Miss — invoke AI reasoning layer (Stage 3 extension)
        # ------------------------------------------------------------------
        # Step 7b: LLM response generation
        # ------------------------------------------------------------------
        ai_result = _try_llm_response(
            customer_message=content,
            customer_name=display_name,
            channel=channel,
            intent=intent,
            kb_results=kb_result,
            customer_context=customer_ctx,
        )

        if ai_result is not None and ai_result.source == "llm":
            response_body = ai_result.content
            ai_used = True
            ai_provider = ai_result.provider
            ai_model = ai_result.model
            tokens_used = ai_result.tokens_used
            ticket_status = "auto-resolved"
            response_source = "llm"
        elif ai_result is not None and ai_result.source == "fallback":
            response_body = ai_result.content
            ticket_status = "pending_review"
            response_source = "fallback"
        else:
            # Hard fallback — should not normally reach here
            response_body = (
                "I don't have specific information about that in my current knowledge base. "
                "I've logged your query and a specialist will provide a detailed answer shortly."
            )
            ticket_status = "pending_review"
            response_source = "fallback"

    # ------------------------------------------------------------------
    # Step 8: Create ticket
    # ------------------------------------------------------------------
    ticket_data = call_tool(
        "create_ticket",
        customer_id=customer.id,
        channel=channel,
        subject=f"[{intent.upper()}] {content[:80]}",
        description=content,
        priority="low",
        status=ticket_status,
        conversation_id=conversation.id,
        db=db,
    )

    # ------------------------------------------------------------------
    # Step 9: Format channel-appropriate response
    # ------------------------------------------------------------------
    formatted = call_tool(
        "send_channel_response",
        message_body=response_body,
        channel=channel,
        customer_name=display_name,
        ticket_ref=ticket_data["ticket_ref"],
    )

    response_text = formatted["response"]

    # ------------------------------------------------------------------
    # Step 10: Store conversation + record metrics
    # ------------------------------------------------------------------
    crud.create_message(db, conversation.id, "customer", content, channel)
    crud.create_message(db, conversation.id, "agent", response_text, channel)

    elapsed_ms = (time.monotonic() - start_time) * 1000

    crud.create_metric(
        db=db,
        channel=channel,
        ticket_id=ticket_data["ticket_id"],
        conversation_id=conversation.id,
        intent=intent,
        escalated=False,
        kb_used=kb_result["matched"],
        kb_topic=kb_topic,
        processing_time_ms=elapsed_ms,
    )

    _record_analytics(
        interaction_id=str(conversation.id),
        channel=channel,
        intent=intent,
        response_source=response_source,
        response_time_ms=elapsed_ms,
        escalated=False,
        kb_used=kb_result["matched"],
        ai_used=ai_used,
        ticket_created=True,
        tokens_used=tokens_used,
    )

    logger.info(
        "RESPONDED | customer=%s | intent=%s | source=%s | ticket=%s | %.1fms",
        customer_id, intent, response_source, ticket_data["ticket_ref"], elapsed_ms,
    )

    return {
        "success": True,
        "escalated": False,
        "escalation_reason": None,
        "escalation_severity": None,
        "ticket": ticket_data,
        "response": response_text,
        "channel": channel,
        "customer": display_name,
        "intent": intent,
        "kb_used": kb_result["matched"],
        "kb_topic": kb_topic,
        "ai_used": ai_used,
        "ai_provider": ai_provider,
        "ai_model": ai_model,
        "tokens_used": tokens_used,
        "response_time_ms": round(elapsed_ms, 2),
        "conversation_id": conversation.id,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _try_llm_response(
    customer_message: str,
    customer_name: str,
    channel: str,
    intent: str,
    kb_results: dict,
    customer_context: dict,
):
    """
    Attempt to generate an LLM response. Returns None on import/config error
    so the caller can apply a simple text fallback instead.
    """
    try:
        from backend.llm.response_generator import ResponseGenerator  # noqa: PLC0415

        generator = ResponseGenerator()
        return generator.generate_response(
            customer_message=customer_message,
            customer_name=customer_name,
            channel=channel,
            intent=intent,
            kb_results=kb_results,
            customer_context=customer_context,
        )
    except ImportError:
        logger.debug("LLM module not available — using text fallback.")
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM response generation failed: %s", exc)
        return None


def _record_analytics(
    interaction_id: str,
    channel: str,
    intent: str,
    response_source: str,
    response_time_ms: float,
    escalated: bool,
    kb_used: bool,
    ai_used: bool,
    ticket_created: bool,
    tokens_used: int = 0,
) -> None:
    """Fire-and-forget analytics recording — never raises."""
    try:
        from backend.analytics.agent_metrics import metrics_collector  # noqa: PLC0415

        metrics_collector.record_interaction(
            interaction_id=interaction_id,
            channel=channel,
            intent=intent,
            response_source=response_source,
            response_time_ms=response_time_ms,
            escalated=escalated,
            kb_used=kb_used,
            ai_used=ai_used,
            ticket_created=ticket_created,
            tokens_used=tokens_used,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Analytics recording skipped: %s", exc)
