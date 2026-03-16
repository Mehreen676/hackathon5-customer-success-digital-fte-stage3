"""
Twilio WhatsApp Integration Client — Customer Success Digital FTE (Stage 3)

Wraps the Twilio REST API for sending outbound WhatsApp messages. Runs in
MOCK mode when Twilio credentials are absent so development works without
a live Twilio account.

===========================================================================
CREDENTIALS REQUIRED FOR LIVE MODE
===========================================================================

1. Create a free Twilio account at https://www.twilio.com/try-twilio
2. Join the WhatsApp Sandbox (Messaging → Try it out → Send a WhatsApp message)
   OR provision a WhatsApp Business sender in a production account
3. Note your Account SID and Auth Token from the Twilio Console dashboard
4. Set environment variables:
      TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      TWILIO_AUTH_TOKEN=your_auth_token
      TWILIO_WHATSAPP_FROM=whatsapp:+14155238886   (Twilio sandbox number)

Install optional SDK dependency:
    pip install twilio

Webhook setup (inbound messages):
    Set your WhatsApp sandbox / number webhook URL to:
        https://your-domain.com/webhooks/whatsapp
    (Method: HTTP POST, Content-Type: application/x-www-form-urlencoded)

Without credentials the client operates in MOCK mode and logs all operations
instead of calling the Twilio API.
===========================================================================
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional Twilio SDK
# ---------------------------------------------------------------------------

try:
    from twilio.rest import Client as TwilioRestClient

    _TWILIO_AVAILABLE = True
except ImportError:
    _TWILIO_AVAILABLE = False
    logger.debug("twilio SDK not installed — TwilioClient will use MOCK mode")


# ---------------------------------------------------------------------------
# TwilioClient
# ---------------------------------------------------------------------------


class TwilioClient:
    """
    Twilio REST client for sending WhatsApp messages.

    Automatically falls back to MOCK mode when:
      - The twilio package is not installed
      - TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN env vars are not set
      - Twilio authentication fails

    In MOCK mode every operation logs what it would have done and returns
    a realistic stub response.
    """

    def __init__(self) -> None:
        self.account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.from_number: str = os.getenv(
            "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"
        )
        self.mock_mode: bool = True
        self._client = None

        if not _TWILIO_AVAILABLE:
            logger.info("TwilioClient: twilio package not installed → MOCK mode")
            return

        if not self.account_sid or not self.auth_token:
            logger.info(
                "TwilioClient: TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not set → MOCK mode"
            )
            return

        try:
            self._client = TwilioRestClient(self.account_sid, self.auth_token)
            # Quick sanity check — fetch account info
            account = self._client.api.accounts(self.account_sid).fetch()
            self.mock_mode = False
            logger.info(
                "TwilioClient: authenticated | account=%s | status=%s",
                self.account_sid[:8] + "...",
                account.status,
            )
        except Exception as exc:
            logger.warning(
                "TwilioClient: authentication failed → MOCK mode | %s", exc
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_whatsapp(
        self,
        to_phone: str,
        body: str,
        media_url: Optional[str] = None,
    ) -> dict:
        """
        Send a WhatsApp message to a customer phone number.

        Args:
            to_phone:  Recipient phone in E.164 format, e.g. '+15551234567'.
                       The 'whatsapp:' prefix is added automatically.
            body:      Message text (max 1600 characters for WhatsApp).
            media_url: Optional public URL of an image or document to attach.

        Returns:
            dict: {"sent": bool, "message_sid": str, "status": str, "mode": str}
        """
        # Normalise phone number — add whatsapp: prefix if missing
        to_wa = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"

        if self.mock_mode:
            logger.info(
                "[MOCK] TwilioClient.send_whatsapp → to=%s | body_len=%d",
                to_wa,
                len(body),
            )
            return {
                "sent": True,
                "message_sid": "SM00000000000000000000000000000000",
                "status": "queued",
                "mode": "mock",
            }

        try:
            kwargs: dict = {
                "from_": self.from_number,
                "to": to_wa,
                "body": body,
            }
            if media_url:
                kwargs["media_url"] = [media_url]

            message = self._client.messages.create(**kwargs)
            logger.info(
                "TwilioClient.send_whatsapp: sent | sid=%s | to=%s | status=%s",
                message.sid,
                to_wa,
                message.status,
            )
            return {
                "sent": True,
                "message_sid": message.sid,
                "status": message.status,
                "mode": "live",
            }
        except Exception as exc:
            logger.error("TwilioClient.send_whatsapp failed: %s", exc)
            return {"sent": False, "error": str(exc), "mode": "live"}

    def send_sms(self, to_phone: str, body: str) -> dict:
        """
        Send a plain SMS (fallback channel when WhatsApp delivery fails).

        Args:
            to_phone: Recipient phone in E.164 format.
            body:     Message text.

        Returns:
            dict: {"sent": bool, "message_sid": str, "status": str, "mode": str}
        """
        sms_from = os.getenv("TWILIO_SMS_FROM", "").strip()

        if self.mock_mode or not sms_from:
            logger.info(
                "[MOCK] TwilioClient.send_sms → to=%s | body_len=%d",
                to_phone,
                len(body),
            )
            return {
                "sent": True,
                "message_sid": "SM_SMS_MOCK_000000000000000000000000",
                "status": "queued",
                "mode": "mock",
            }

        try:
            message = self._client.messages.create(
                from_=sms_from, to=to_phone, body=body
            )
            return {
                "sent": True,
                "message_sid": message.sid,
                "status": message.status,
                "mode": "live",
            }
        except Exception as exc:
            logger.error("TwilioClient.send_sms failed: %s", exc)
            return {"sent": False, "error": str(exc), "mode": "live"}

    def get_message_status(self, message_sid: str) -> dict:
        """
        Retrieve the delivery status of a previously sent message.

        Args:
            message_sid: The Twilio MessageSid to look up.

        Returns:
            dict: {"sid": str, "status": str, "error_code": str|None, "mode": str}
        """
        if self.mock_mode:
            logger.info(
                "[MOCK] TwilioClient.get_message_status → sid=%s", message_sid
            )
            return {
                "sid": message_sid,
                "status": "delivered",
                "error_code": None,
                "mode": "mock",
            }

        try:
            msg = self._client.messages(message_sid).fetch()
            return {
                "sid": msg.sid,
                "status": msg.status,
                "error_code": msg.error_code,
                "mode": "live",
            }
        except Exception as exc:
            logger.error("TwilioClient.get_message_status failed: %s", exc)
            return {"sid": message_sid, "error": str(exc), "mode": "live"}

    @property
    def is_live(self) -> bool:
        """True when connected to the real Twilio API."""
        return not self.mock_mode


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

twilio_client = TwilioClient()
