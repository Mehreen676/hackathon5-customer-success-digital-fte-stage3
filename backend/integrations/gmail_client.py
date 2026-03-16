"""
Gmail Integration Client — Customer Success Digital FTE (Stage 3)

Wraps the Google Gmail API for sending support replies and fetching inbound
email content. Runs in MOCK mode when Google credentials are absent so the
full system works in development without Google Cloud access.

===========================================================================
CREDENTIALS REQUIRED FOR LIVE MODE
===========================================================================

1. Create or open a Google Cloud project at https://console.cloud.google.com
2. Enable the Gmail API (APIs & Services → Library → Gmail API → Enable)
3. Create a Service Account:
   - IAM & Admin → Service Accounts → Create Service Account
   - Grant "Gmail API" access with domain-wide delegation
4. Download the service account key (JSON) and place it on your server
5. In Google Workspace Admin, authorize the service account for the
   Gmail API scope: https://www.googleapis.com/auth/gmail.send
6. Set environment variables:
      GMAIL_CREDENTIALS_PATH=/path/to/service_account_key.json
      GMAIL_USER_EMAIL=support@nexora.io

Install optional SDK dependency:
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

Without credentials the client operates in MOCK mode and logs all operations
instead of calling the Gmail API. All code paths remain exercisable in tests.
===========================================================================
"""

from __future__ import annotations

import base64
import email.mime.multipart
import email.mime.text
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional Google SDK
# ---------------------------------------------------------------------------

try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account as _sa

    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False
    logger.debug(
        "google-api-python-client not installed — GmailClient will use MOCK mode"
    )

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


# ---------------------------------------------------------------------------
# GmailClient
# ---------------------------------------------------------------------------


class GmailClient:
    """
    Gmail API wrapper for sending support replies and fetching inbound messages.

    Automatically falls back to MOCK mode when:
      - The google-api-python-client package is not installed
      - GMAIL_CREDENTIALS_PATH env var is not set or the file is missing
      - Authentication fails for any reason

    In MOCK mode every operation logs what it would have done and returns
    a realistic stub response. This keeps development and CI fully functional
    without Google Cloud credentials.
    """

    def __init__(self) -> None:
        self.user_email: str = os.getenv("GMAIL_USER_EMAIL", "support@nexora.io")
        self.mock_mode: bool = True
        self._service = None

        if not _GOOGLE_AVAILABLE:
            logger.info(
                "GmailClient: google-api-python-client not installed → MOCK mode"
            )
            return

        credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", "").strip()
        if not credentials_path or not os.path.exists(credentials_path):
            logger.info(
                "GmailClient: GMAIL_CREDENTIALS_PATH not set or file not found → MOCK mode"
            )
            return

        try:
            delegated_email = os.getenv("GMAIL_DELEGATED_EMAIL", self.user_email)
            creds = _sa.Credentials.from_service_account_file(
                credentials_path,
                scopes=GMAIL_SCOPES,
                subject=delegated_email,
            )
            self._service = build("gmail", "v1", credentials=creds)
            self.mock_mode = False
            logger.info(
                "GmailClient: authenticated as %s (delegated: %s)",
                self.user_email,
                delegated_email,
            )
        except Exception as exc:
            logger.warning(
                "GmailClient: authentication failed → MOCK mode | %s", exc
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_reply(
        self,
        to_email: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
    ) -> dict:
        """
        Send an email reply from the support mailbox.

        Args:
            to_email:     Recipient email address.
            subject:      Subject line (prepend 'Re: ' for replies).
            body:         Plain-text reply body.
            thread_id:    Gmail thread ID to keep the email in-thread.
            in_reply_to:  Message-ID header of the original email.

        Returns:
            dict: {"sent": bool, "message_id": str, "mode": "live"|"mock"}
        """
        if self.mock_mode:
            logger.info(
                "[MOCK] GmailClient.send_reply → to=%s | subject=%s | thread=%s",
                to_email,
                subject[:60],
                thread_id,
            )
            return {"sent": True, "message_id": "mock_msg_id_001", "mode": "mock"}

        try:
            msg = email.mime.text.MIMEText(body, "plain")
            msg["To"] = to_email
            msg["From"] = self.user_email
            msg["Subject"] = subject
            if in_reply_to:
                msg["In-Reply-To"] = in_reply_to
                msg["References"] = in_reply_to

            encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            body_payload: dict = {"raw": encoded}
            if thread_id:
                body_payload["threadId"] = thread_id

            result = (
                self._service.users()
                .messages()
                .send(userId=self.user_email, body=body_payload)
                .execute()
            )
            logger.info(
                "GmailClient.send_reply: sent | id=%s | to=%s",
                result.get("id"),
                to_email,
            )
            return {"sent": True, "message_id": result.get("id", ""), "mode": "live"}

        except Exception as exc:
            logger.error("GmailClient.send_reply failed: %s", exc)
            return {"sent": False, "error": str(exc), "mode": "live"}

    def fetch_message(self, message_id: str) -> dict:
        """
        Fetch full email content by Gmail message ID.

        In production this is called after receiving a Pub/Sub push notification
        that contains only the message ID. The full email body is retrieved here.

        Args:
            message_id: The Gmail message ID from the Pub/Sub notification.

        Returns:
            dict: {"from_email", "from_name", "subject", "body",
                   "thread_id", "message_id", "mode"}
            On error returns {"error": str, "message_id": str, "mode": "live"}.
        """
        if self.mock_mode:
            logger.info("[MOCK] GmailClient.fetch_message → id=%s", message_id)
            return {
                "from_email": "customer@example.com",
                "from_name": "Test Customer",
                "subject": "Mock Support Request",
                "body": (
                    "Hi Nexora team,\n\n"
                    "This is a mock email generated in development mode "
                    "(GMAIL_CREDENTIALS_PATH not configured).\n\n"
                    "I need help with my account.\n\nThanks"
                ),
                "thread_id": f"mock_thread_{message_id[:8]}",
                "message_id": message_id,
                "mode": "mock",
            }

        try:
            msg = (
                self._service.users()
                .messages()
                .get(userId=self.user_email, id=message_id, format="full")
                .execute()
            )
            headers = {
                h["name"].lower(): h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            body = self._extract_body(msg)
            return {
                "from_email": self._parse_email(headers.get("from", "")),
                "from_name": self._parse_name(headers.get("from", "")),
                "subject": headers.get("subject", ""),
                "body": body,
                "thread_id": msg.get("threadId", ""),
                "message_id": headers.get("message-id", message_id),
                "mode": "live",
            }
        except Exception as exc:
            logger.error("GmailClient.fetch_message failed: %s", exc)
            return {"error": str(exc), "message_id": message_id, "mode": "live"}

    def list_history(self, start_history_id: str) -> list[dict]:
        """
        List Gmail history records since a given historyId.

        Used to discover new message IDs from a Pub/Sub notification that
        carries only a historyId rather than a message ID.

        Args:
            start_history_id: The historyId from the Pub/Sub notification.

        Returns:
            List of dicts, each with 'message_id' and 'type'.
        """
        if self.mock_mode:
            logger.info(
                "[MOCK] GmailClient.list_history → historyId=%s", start_history_id
            )
            return [{"message_id": f"mock_msg_{start_history_id[:8]}", "type": "messageAdded"}]

        try:
            result = (
                self._service.users()
                .history()
                .list(
                    userId=self.user_email,
                    startHistoryId=start_history_id,
                    historyTypes=["messageAdded"],
                )
                .execute()
            )
            records = []
            for history in result.get("history", []):
                for added in history.get("messagesAdded", []):
                    records.append(
                        {"message_id": added["message"]["id"], "type": "messageAdded"}
                    )
            return records
        except Exception as exc:
            logger.error("GmailClient.list_history failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_body(self, message: dict) -> str:
        """Extract plain-text body from a Gmail message payload."""
        payload = message.get("payload", {})
        # Single-part message
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        # Multi-part: look for text/plain part
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                part_data = part.get("body", {}).get("data", "")
                if part_data:
                    return base64.urlsafe_b64decode(part_data + "==").decode(
                        "utf-8", errors="replace"
                    )
        return ""

    def _parse_email(self, from_header: str) -> str:
        """Extract email address from 'Name <email>' format."""
        if "<" in from_header:
            return from_header.split("<")[-1].rstrip(">").strip()
        return from_header.strip()

    def _parse_name(self, from_header: str) -> str:
        """Extract display name from 'Name <email>' format."""
        if "<" in from_header:
            return from_header.split("<")[0].strip().strip('"').strip("'")
        return ""

    @property
    def is_live(self) -> bool:
        """True when connected to the real Gmail API."""
        return not self.mock_mode


# ---------------------------------------------------------------------------
# Module-level singleton — import and use directly
# ---------------------------------------------------------------------------

gmail_client = GmailClient()
