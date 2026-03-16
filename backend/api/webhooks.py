"""
Webhook API Routes — Customer Success Digital FTE (Stage 3)

Handles inbound webhooks from external services:

    POST /webhooks/gmail        Google Cloud Pub/Sub push notification (new email)
    POST /webhooks/whatsapp     Twilio WhatsApp form-encoded message

Both endpoints:
  1. Parse and validate the inbound payload
  2. Normalise to the common NormalizedMessage format
  3. Run the existing 10-step agent workflow
  4. Return a JSON acknowledgment

Returning HTTP 200 is critical for Pub/Sub (else it retries) and is
expected by Twilio (non-2xx triggers a retry after a short delay).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.agents.customer_success_agent import run_agent
from backend.channels.gmail_handler import gmail_handler
from backend.channels.whatsapp_handler import whatsapp_handler
from backend.database.database import get_db
from backend.integrations.gmail_client import gmail_client
from backend.integrations.twilio_client import twilio_client
from backend.schemas.message_schema import GmailMessageRequest, WhatsAppMessageRequest
from backend.webhooks.gmail_webhook import parse_pubsub_notification
from backend.webhooks.whatsapp_webhook import parse_twilio_webhook, validate_twilio_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class WebhookAck(BaseModel):
    """Acknowledgment response returned by all webhook endpoints."""

    received: bool
    channel: str
    status: str
    message_sid: Optional[str] = None
    ticket_ref: Optional[str] = None
    escalated: Optional[bool] = None
    mode: str = "live"


# ---------------------------------------------------------------------------
# Pub/Sub payload models (used only for Gmail)
# ---------------------------------------------------------------------------


class _PubSubMessage(BaseModel):
    data: str = ""
    messageId: str = ""
    publishTime: str = ""


class GmailPubSubPayload(BaseModel):
    """
    Google Cloud Pub/Sub push notification body.

    Google POSTs this to /webhooks/gmail for every new Gmail event.
    """

    message: _PubSubMessage
    subscription: str = ""


# ---------------------------------------------------------------------------
# POST /webhooks/gmail
# ---------------------------------------------------------------------------


@router.post(
    "/gmail",
    response_model=WebhookAck,
    summary="Receive Gmail Pub/Sub push notification",
)
async def gmail_webhook(
    payload: GmailPubSubPayload,
    db: Session = Depends(get_db),
) -> WebhookAck:
    """
    Endpoint for Google Cloud Pub/Sub push notifications triggered by new Gmail.

    **Setup (Google Cloud)**

    1. Create a Pub/Sub topic: `gcloud pubsub topics create gmail-notifications`
    2. Grant Gmail permission to publish:
       `serviceAccount:gmail-api-push@system.gserviceaccount.com`
    3. Create a push subscription pointing to `https://your-host/webhooks/gmail`
    4. Call `users.watch()` on the Gmail mailbox

    **Behavior**

    - Decodes the base64 Pub/Sub data field
    - Fetches the email content via GmailClient (MOCK in development)
    - Normalises and processes through the AI agent workflow
    - Returns 200 OK to acknowledge (Pub/Sub retries on non-2xx)

    **Credentials**

    Set `GMAIL_CREDENTIALS_PATH` and `GMAIL_USER_EMAIL` env vars for live mode.
    Without them the endpoint works in MOCK mode (no Gmail API calls).
    """
    logger.info(
        "POST /webhooks/gmail | pubsub_message_id=%s",
        payload.message.messageId,
    )

    # Step 1: Decode the Pub/Sub notification
    parsed = parse_pubsub_notification(
        {
            "message": payload.message.model_dump(),
            "subscription": payload.subscription,
        }
    )

    if not parsed:
        logger.warning("Gmail webhook: failed to parse Pub/Sub payload → acking anyway")
        # Return 200 to prevent Pub/Sub retries for permanently bad messages
        return WebhookAck(
            received=False,
            channel="email",
            status="parse_error",
            mode=("mock" if gmail_client.mock_mode else "live"),
        )

    # Step 2: Fetch the actual email
    # In mock mode: GmailClient returns a stub email
    # In live mode: GmailClient.list_history → then fetch_message
    gmail_msg = _fetch_email(parsed)

    if "error" in gmail_msg and not gmail_msg.get("from_email"):
        logger.error(
            "Gmail webhook: could not fetch email | error=%s",
            gmail_msg.get("error"),
        )
        return WebhookAck(
            received=False,
            channel="email",
            status="fetch_error",
            mode="live",
        )

    # Step 3: Normalise and run agent workflow
    request = GmailMessageRequest(
        from_email=gmail_msg.get("from_email", "unknown@example.com"),
        from_name=gmail_msg.get("from_name", ""),
        subject=gmail_msg.get("subject", "Support Request"),
        body=gmail_msg.get("body", ""),
    )
    normalized = gmail_handler.normalize(request)
    result = run_agent(normalized, db)

    # Step 4: (Optional) Send reply via Gmail API in live mode
    if not gmail_client.mock_mode and result.get("success") and result.get("response"):
        reply_subject = request.subject
        if not reply_subject.startswith("Re: "):
            reply_subject = f"Re: {reply_subject}"
        gmail_client.send_reply(
            to_email=request.from_email,
            subject=reply_subject,
            body=result["response"],
            thread_id=gmail_msg.get("thread_id"),
        )

    ticket_ref = (
        result.get("ticket", {}).get("ticket_ref")
        if result.get("success")
        else None
    )

    logger.info(
        "Gmail webhook processed | from=%s | ticket=%s | escalated=%s",
        request.from_email,
        ticket_ref,
        result.get("escalated"),
    )

    return WebhookAck(
        received=True,
        channel="email",
        status="processed",
        ticket_ref=ticket_ref,
        escalated=result.get("escalated"),
        mode=("mock" if gmail_client.mock_mode else "live"),
    )


def _fetch_email(parsed_notification: dict) -> dict:
    """
    Fetch full email from Gmail given a parsed Pub/Sub notification.

    Tries list_history first (preferred — gives us message IDs from historyId),
    falls back to treating history_id as message_id for mock/testing scenarios.
    """
    history_id = parsed_notification.get("history_id", "")
    message_id = parsed_notification.get("message_id", "")

    if not gmail_client.mock_mode and history_id:
        history_records = gmail_client.list_history(history_id)
        if history_records:
            first_msg_id = history_records[0]["message_id"]
            return gmail_client.fetch_message(first_msg_id)

    # Mock mode or fallback: use the Pub/Sub message_id directly
    return gmail_client.fetch_message(message_id or history_id or "mock")


# ---------------------------------------------------------------------------
# POST /webhooks/whatsapp
# ---------------------------------------------------------------------------


@router.post(
    "/whatsapp",
    response_model=WebhookAck,
    summary="Receive Twilio WhatsApp message webhook",
)
async def whatsapp_webhook(
    request: Request,
    From: str = Form(..., description="Sender number, e.g. 'whatsapp:+15551234567'"),
    Body: str = Form(..., description="Message body text"),
    MessageSid: str = Form(default="", description="Twilio MessageSid (SM...)"),
    AccountSid: str = Form(default="", description="Twilio AccountSid (AC...)"),
    To: str = Form(default="", description="Destination number"),
    NumMedia: str = Form(default="0", description="Number of media attachments"),
    ProfileName: str = Form(default="", description="WhatsApp display name"),
    WaId: str = Form(default="", description="WhatsApp ID (phone without '+')"),
    x_twilio_signature: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> WebhookAck:
    """
    Endpoint for Twilio WhatsApp inbound message webhooks.

    **Setup (Twilio)**

    1. In the Twilio console, go to Messaging → Try it out → Send a WhatsApp message
       (sandbox) or configure a WhatsApp sender (production).
    2. Set the webhook URL to `https://your-host/webhooks/whatsapp`
    3. Method: HTTP POST

    **Signature Validation**

    In production set `TWILIO_AUTH_TOKEN` to enable X-Twilio-Signature validation.
    Without it validation is skipped (development / testing mode).

    **Credentials**

    Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_WHATSAPP_FROM` env vars
    to enable outbound reply delivery.

    **Behavior**

    - Validates Twilio signature (if auth token configured)
    - Parses standard Twilio form fields
    - Runs the AI agent workflow
    - Optionally sends reply via Twilio WhatsApp (live mode)
    - Returns JSON ack (Twilio ignores body for WhatsApp but expects 200)
    """
    logger.info(
        "POST /webhooks/whatsapp | From=%s | MessageSid=%s",
        From,
        MessageSid,
    )

    # Validate Twilio signature (no-op in dev mode)
    form_data = {
        "From": From,
        "Body": Body,
        "MessageSid": MessageSid,
        "AccountSid": AccountSid,
        "To": To,
        "NumMedia": NumMedia,
        "ProfileName": ProfileName,
        "WaId": WaId,
    }
    if not validate_twilio_signature(str(request.url), form_data, x_twilio_signature or ""):
        logger.warning("WhatsApp webhook: invalid Twilio signature from %s", From)
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # Parse the form fields
    parsed = parse_twilio_webhook(
        from_field=From,
        body=Body,
        message_sid=MessageSid,
        account_sid=AccountSid,
        to_field=To,
        num_media=NumMedia,
        profile_name=ProfileName,
        wa_id=WaId,
    )

    if not parsed:
        return WebhookAck(
            received=False,
            channel="whatsapp",
            status="parse_error",
            message_sid=MessageSid or None,
            mode=("mock" if twilio_client.mock_mode else "live"),
        )

    # Normalise and run agent workflow
    wa_request = WhatsAppMessageRequest(
        from_phone=parsed["from_phone"],
        message_text=parsed["message_text"],
    )
    normalized = whatsapp_handler.normalize(wa_request)
    result = run_agent(normalized, db)

    # (Optional) Send reply via Twilio in live mode
    if not twilio_client.mock_mode and result.get("success") and result.get("response"):
        twilio_client.send_whatsapp(
            to_phone=parsed["from_phone"],
            body=result["response"],
        )

    ticket_ref = (
        result.get("ticket", {}).get("ticket_ref")
        if result.get("success")
        else None
    )

    logger.info(
        "WhatsApp webhook processed | from=%s | ticket=%s | escalated=%s",
        parsed["from_phone"],
        ticket_ref,
        result.get("escalated"),
    )

    return WebhookAck(
        received=True,
        channel="whatsapp",
        status="processed",
        message_sid=MessageSid or None,
        ticket_ref=ticket_ref,
        escalated=result.get("escalated"),
        mode=("mock" if twilio_client.mock_mode else "live"),
    )
