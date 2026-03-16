"""
WhatsApp / Twilio Webhook Parser — Customer Success Digital FTE (Stage 3)

Parses inbound Twilio WhatsApp webhook payloads and optionally validates
the request signature to confirm authenticity.

Twilio WhatsApp Webhook Flow
─────────────────────────────
1. Customer sends a WhatsApp message to your Twilio number.
2. Twilio makes a form-encoded HTTP POST to /webhooks/whatsapp.
3. This parser extracts the relevant fields.
4. The webhook route normalises and forwards to the agent pipeline.

Typical Twilio Webhook Form Fields
────────────────────────────────────
From:          whatsapp:+15551234567
To:            whatsapp:+14155238886
Body:          Hi, I need help with my invoice
MessageSid:    SM00000000000000000000000000000000
AccountSid:    AC00000000000000000000000000000000
NumMedia:      0
ProfileName:   John Doe                           (WhatsApp display name, if available)
WaId:          15551234567                        (WhatsApp ID / phone without + prefix)

Signature Validation
──────────────────────
Twilio signs every request using HMAC-SHA1 of the full URL + sorted form params.
The signature is sent in the X-Twilio-Signature header.

In development (TWILIO_AUTH_TOKEN not set) validation is skipped.
In production set TWILIO_AUTH_TOKEN and the validator runs automatically.

Reference: https://www.twilio.com/docs/usage/webhooks/webhooks-security
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional Twilio signature validator
# ---------------------------------------------------------------------------

try:
    from twilio.request_validator import RequestValidator as _TwilioValidator

    _TWILIO_VALIDATOR_AVAILABLE = True
except ImportError:
    _TWILIO_VALIDATOR_AVAILABLE = False


def validate_twilio_signature(
    url: str,
    params: dict,
    signature: str,
) -> bool:
    """
    Validate the X-Twilio-Signature header on an inbound Twilio webhook.

    Args:
        url:       Full request URL including scheme and host.
        params:    Form parameters as a plain dict.
        signature: Value of the X-Twilio-Signature header.

    Returns:
        True  — signature valid, or validation skipped (no auth token / no SDK).
        False — signature invalid (reject the request in production).
    """
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()

    if not auth_token:
        logger.debug(
            "Twilio signature validation skipped: TWILIO_AUTH_TOKEN not set (dev mode)"
        )
        return True

    if not _TWILIO_VALIDATOR_AVAILABLE:
        logger.debug(
            "Twilio signature validation skipped: twilio SDK not installed"
        )
        return True

    try:
        validator = _TwilioValidator(auth_token)
        result = validator.validate(url, params, signature)
        if not result:
            logger.warning(
                "Twilio signature validation FAILED | url=%s | sig=%s",
                url,
                signature[:20] if signature else "(empty)",
            )
        return result
    except Exception as exc:
        logger.error("Twilio signature validation error: %s", exc)
        return False


def parse_twilio_webhook(
    from_field: str,
    body: str,
    message_sid: str = "",
    account_sid: str = "",
    to_field: str = "",
    num_media: str = "0",
    profile_name: str = "",
    wa_id: str = "",
) -> Optional[dict]:
    """
    Parse individual Twilio webhook fields into a normalised dict.

    Args:
        from_field:   'From' field — e.g. 'whatsapp:+15551234567'.
        body:         'Body' field — the inbound message text.
        message_sid:  'MessageSid' — Twilio message identifier (SM...).
        account_sid:  'AccountSid' — Twilio account identifier (AC...).
        to_field:     'To' field — your Twilio WhatsApp number.
        num_media:    'NumMedia' — number of attached media items.
        profile_name: 'ProfileName' — WhatsApp display name (optional).
        wa_id:        'WaId' — WhatsApp ID / phone without + prefix.

    Returns:
        dict with keys:
            from_phone    str   E.164 phone number (with '+')
            to_phone      str   Destination number
            message_text  str   Cleaned message body
            message_sid   str   Twilio MessageSid
            account_sid   str   Twilio AccountSid
            has_media     bool  True if NumMedia > 0
            profile_name  str   Customer WhatsApp display name (may be empty)
            wa_id         str   WhatsApp ID
        Returns None if required fields are missing.
    """
    if not from_field or not body:
        logger.warning(
            "Twilio webhook: missing required fields | From=%r | Body=%r",
            from_field,
            body[:40] if body else "",
        )
        return None

    # Strip the 'whatsapp:' prefix — we store plain E.164 numbers internally
    from_phone = from_field.replace("whatsapp:", "").strip()
    to_phone = to_field.replace("whatsapp:", "").strip()

    # Ensure leading '+' for E.164 normalisation
    if from_phone and not from_phone.startswith("+"):
        from_phone = "+" + from_phone

    return {
        "from_phone": from_phone,
        "to_phone": to_phone,
        "message_text": body.strip(),
        "message_sid": message_sid,
        "account_sid": account_sid,
        "has_media": int(num_media or "0") > 0,
        "profile_name": profile_name.strip(),
        "wa_id": wa_id.strip(),
    }


def build_demo_twilio_payload(
    from_phone: str = "+15551234567",
    body: str = "Hi, I need help with my account",
    message_sid: str = "SM00000000000000000000000000000001",
) -> dict:
    """
    Build a realistic Twilio webhook form-data dict for testing.

    Args:
        from_phone:  Sender phone in E.164 (will have 'whatsapp:' prepended).
        body:        Message text.
        message_sid: A fake Twilio MessageSid.

    Returns:
        dict of form fields matching what Twilio sends.
    """
    return {
        "From": f"whatsapp:{from_phone}",
        "To": "whatsapp:+14155238886",
        "Body": body,
        "MessageSid": message_sid,
        "AccountSid": "AC00000000000000000000000000000000",
        "NumMedia": "0",
        "ProfileName": "Test Customer",
        "WaId": from_phone.lstrip("+"),
    }
