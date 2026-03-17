"""
Support API Endpoints — Customer Success Digital FTE (Stage 3)

Defines the /support/* routes that accept inbound customer messages
from all channels and route them through the agent workflow.

Endpoints:
    POST /support/message          — Generic unified message endpoint
    POST /support/gmail            — Gmail channel endpoint
    POST /support/whatsapp         — WhatsApp channel endpoint
    POST /support/webform          — Web form channel endpoint
    POST /support/submit           — Web support form (user-facing)
    GET  /support/ticket/{ref}     — Ticket status lookup by ticket reference
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.agents.customer_success_agent import run_agent
from backend.channels.gmail_handler import gmail_handler
from backend.channels.webform_handler import webform_handler
from backend.channels.whatsapp_handler import whatsapp_handler
from backend.database.database import get_db
from backend.database.crud import get_all_tickets, get_ticket_by_ref
from backend.schemas.message_schema import (
    GenericMessageRequest,
    GmailMessageRequest,
    NormalizedMessage,
    WebFormRequest,
    WhatsAppMessageRequest,
)
from backend.schemas.response_schema import AgentResponse, TicketStatusResponse
from backend.schemas.ticket_schema import TicketOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["Support"])


def _build_response(result: dict) -> AgentResponse:
    """Convert the raw workflow result dict into the AgentResponse schema."""
    if not result.get("success"):
        raise HTTPException(
            status_code=422,
            detail=result.get("error", "Agent processing failed"),
        )

    ticket_data = result["ticket"]

    ticket_out = TicketOut(
        ticket_ref=ticket_data["ticket_ref"],
        status=ticket_data["status"],
        priority=ticket_data["priority"],
        escalated=ticket_data["escalated"],
        escalation_reason=result.get("escalation_reason"),
        escalation_severity=result.get("escalation_severity"),
        assigned_team=ticket_data.get("assigned_team"),
        channel=ticket_data["channel"],
        created_at=ticket_data["created_at"],
    )

    return AgentResponse(
        success=True,
        channel=result["channel"],
        customer=result["customer"],
        intent=result.get("intent"),
        escalated=result["escalated"],
        escalation_reason=result.get("escalation_reason"),
        escalation_severity=result.get("escalation_severity"),
        kb_used=result["kb_used"],
        kb_topic=result.get("kb_topic"),
        ticket=ticket_out,
        response=result["response"],
        conversation_id=result["conversation_id"],
    )


# ---------------------------------------------------------------------------
# POST /support/message — generic unified endpoint
# ---------------------------------------------------------------------------

@router.post("/message", response_model=AgentResponse)
def handle_message(
    request: GenericMessageRequest,
    db: Session = Depends(get_db),
) -> AgentResponse:
    """
    Generic message endpoint. Accepts any channel in the request body.
    Use the channel-specific endpoints when the source is known.
    """
    logger.info(
        "POST /support/message | customer=%s | channel=%s",
        request.customer_id, request.channel
    )

    normalized = NormalizedMessage(
        customer_id=request.customer_id,
        channel=request.channel,
        content=request.content,
        metadata=request.metadata,
    )

    result = run_agent(normalized, db)
    return _build_response(result)


# ---------------------------------------------------------------------------
# POST /support/gmail
# ---------------------------------------------------------------------------

@router.post("/gmail", response_model=AgentResponse)
def handle_gmail(
    request: GmailMessageRequest,
    db: Session = Depends(get_db),
) -> AgentResponse:
    """
    Gmail channel endpoint. Accepts simulated Gmail webhook payloads.
    Stage 3: Will be triggered by real Gmail push notifications.
    """
    logger.info(
        "POST /support/gmail | from=%s | subject=%s",
        request.from_email, request.subject[:50]
    )

    normalized = gmail_handler.normalize(request)
    result = run_agent(normalized, db)
    return _build_response(result)


# ---------------------------------------------------------------------------
# POST /support/whatsapp
# ---------------------------------------------------------------------------

@router.post("/whatsapp", response_model=AgentResponse)
def handle_whatsapp(
    request: WhatsAppMessageRequest,
    db: Session = Depends(get_db),
) -> AgentResponse:
    """
    WhatsApp channel endpoint. Accepts simulated Twilio WhatsApp webhooks.
    Stage 3: Will be triggered by real Twilio webhook events.
    """
    logger.info(
        "POST /support/whatsapp | from=%s | length=%d",
        request.from_phone, len(request.message_text)
    )

    normalized = whatsapp_handler.normalize(request)
    result = run_agent(normalized, db)
    return _build_response(result)


# ---------------------------------------------------------------------------
# POST /support/webform
# ---------------------------------------------------------------------------

@router.post("/webform", response_model=AgentResponse)
def handle_webform(
    request: WebFormRequest,
    db: Session = Depends(get_db),
) -> AgentResponse:
    """
    Web form channel endpoint. Accepts submissions from the Nexora support form.
    Stage 3: Triggers email confirmation delivery to the submitter.
    """
    logger.info(
        "POST /support/webform | from=%s | subject=%s",
        request.email, request.subject[:50]
    )

    normalized = webform_handler.normalize(request)
    result = run_agent(normalized, db)
    return _build_response(result)


# ---------------------------------------------------------------------------
# POST /support/submit  — user-facing web support form
# ---------------------------------------------------------------------------


@router.post(
    "/submit",
    response_model=AgentResponse,
    summary="Submit a support request via the web form",
)
def submit_support_form(
    request: WebFormRequest,
    db: Session = Depends(get_db),
) -> AgentResponse:
    """
    User-facing support form submission endpoint.

    Accepts the same payload as POST /support/webform but is intended for
    the public-facing support page at /support.  The response includes the
    ticket reference that customers can use to check status later.

    The `ticket.ticket_ref` field in the response is the reference the
    customer should save, e.g. TKT-A1B2C3D4.
    """
    logger.info(
        "POST /support/submit | from=%s | subject=%s",
        request.email,
        request.subject[:50],
    )
    normalized = webform_handler.normalize(request)
    result = run_agent(normalized, db)
    return _build_response(result)


# ---------------------------------------------------------------------------
# GET /support/ticket/{ticket_ref}  — ticket status lookup
# ---------------------------------------------------------------------------


@router.get(
    "/ticket/{ticket_ref}",
    response_model=TicketStatusResponse,
    summary="Look up ticket status by reference",
)
def get_ticket_status(
    ticket_ref: str,
    db: Session = Depends(get_db),
) -> TicketStatusResponse:
    """
    Retrieve the current status of a support ticket by its reference number.

    The ticket reference is returned in the `ticket.ticket_ref` field of
    any POST /support/* response.  Customers can use this endpoint to check
    the status of their request without logging in.

    Returns 404 if the reference is not found.
    """
    ticket = get_ticket_by_ref(db, ticket_ref.upper())
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail=f"Ticket '{ticket_ref}' not found.",
        )

    # Retrieve the most recent agent response from the conversation
    latest_response: str | None = None
    if ticket.conversation:
        agent_messages = [
            m for m in ticket.conversation.messages if m.role == "agent"
        ]
        if agent_messages:
            latest_response = agent_messages[-1].content

    customer_name = ticket.customer.name if ticket.customer else "Unknown"

    return TicketStatusResponse(
        ticket_ref=ticket.ticket_ref,
        status=ticket.status,
        priority=ticket.priority,
        escalated=ticket.escalated,
        channel=ticket.channel,
        subject=ticket.subject,
        created_at=ticket.created_at,
        customer_name=customer_name,
        assigned_team=ticket.assigned_team,
        escalation_reason=ticket.escalation_reason,
        latest_response=latest_response,
    )


# ---------------------------------------------------------------------------
# GET /support/tickets  — list all tickets (dashboard)
# ---------------------------------------------------------------------------


@router.get("/tickets", summary="List recent support tickets")
def list_tickets(
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    Return the most recent support tickets for the dashboard ticket panel.

    Each record includes: ticket_ref, customer, subject, priority, status,
    channel, escalated, created_at.
    """
    tickets = get_all_tickets(db, limit=limit)
    return [
        {
            "ticket_ref": t.ticket_ref,
            "customer": t.customer.name if t.customer else "Unknown",
            "subject": t.subject,
            "priority": t.priority,
            "status": t.status,
            "channel": t.channel,
            "escalated": t.escalated,
            "created_at": (
                t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else ""
            ),
            "description": t.description or "",
        }
        for t in tickets
    ]
