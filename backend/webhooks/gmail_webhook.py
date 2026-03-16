"""
Gmail Webhook Parser — Customer Success Digital FTE (Stage 3)

Parses inbound Google Cloud Pub/Sub push notifications triggered by Gmail.

Gmail Push Notification Flow
─────────────────────────────
1. Set up a Google Cloud Pub/Sub topic and grant Gmail permission to publish.
2. Create a push subscription pointing to POST /webhooks/gmail.
3. Call users.watch() on the Gmail mailbox to subscribe to new-message events.
4. Google POSTs a Pub/Sub notification here for each new email.
5. This parser decodes the notification and returns structured fields.
6. The webhook route then calls GmailClient.fetch_message() to get the body.

Pub/Sub Push Notification Shape
─────────────────────────────────
POST /webhooks/gmail
Content-Type: application/json

{
    "message": {
        "data": "<base64url-encoded JSON string>",
        "messageId": "1234567890123456",
        "publishTime": "2024-06-01T12:00:00.000Z"
    },
    "subscription": "projects/my-project/subscriptions/gmail-push-sub"
}

Decoded "data" payload (Gmail-specific):
{
    "emailAddress": "support@nexora.io",
    "historyId": "9876543"
}

Note: The historyId identifies which history records changed. Use
GmailClient.list_history(historyId) to discover new message IDs, then
GmailClient.fetch_message(messageId) to get the full email content.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def parse_pubsub_notification(payload: dict) -> Optional[dict]:
    """
    Decode a Google Cloud Pub/Sub push notification payload from Gmail.

    Args:
        payload: The raw POST body dict from Google Pub/Sub.
                 Expected keys: "message" (dict), "subscription" (str).

    Returns:
        dict with keys:
            email_address   str   The watched mailbox address
            history_id      str   Gmail historyId for listing new messages
            message_id      str   Pub/Sub messageId (for deduplication)
            publish_time    str   ISO-8601 publish timestamp
            subscription    str   Full Pub/Sub subscription resource name
        Returns None if the payload is malformed.
    """
    try:
        message = payload.get("message") or {}
        raw_data = message.get("data", "")
        subscription = payload.get("subscription", "")

        if not raw_data:
            logger.warning("Gmail webhook: Pub/Sub message has no 'data' field")
            return None

        # Google Pub/Sub encodes the data as base64url (may lack padding)
        padded = raw_data + "=" * (-len(raw_data) % 4)
        decoded_bytes = base64.urlsafe_b64decode(padded)
        data: dict = json.loads(decoded_bytes.decode("utf-8"))

        return {
            "email_address": data.get("emailAddress", ""),
            "history_id": str(data.get("historyId", "")),
            "message_id": message.get("messageId", ""),
            "publish_time": message.get("publishTime", ""),
            "subscription": subscription,
        }

    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.error(
            "Gmail webhook: failed to parse Pub/Sub notification | error=%s | payload=%s",
            exc,
            str(payload)[:200],
        )
        return None


def extract_sender_info(gmail_message: dict) -> dict:
    """
    Extract normalised sender information from a fetched Gmail message dict.

    Accepts the dict returned by GmailClient.fetch_message() and returns
    the fields needed to construct a GmailMessageRequest.

    Args:
        gmail_message: Result from GmailClient.fetch_message().

    Returns:
        dict with keys: from_email, from_name, subject, body,
                        thread_id, message_id.
    """
    return {
        "from_email": gmail_message.get("from_email") or "unknown@example.com",
        "from_name": gmail_message.get("from_name") or "",
        "subject": gmail_message.get("subject") or "Support Request",
        "body": gmail_message.get("body") or "",
        "thread_id": gmail_message.get("thread_id") or "",
        "message_id": gmail_message.get("message_id") or "",
    }


def build_demo_pubsub_payload(
    email_address: str = "support@nexora.io",
    history_id: str = "1234567",
    message_id: str = "msg001",
) -> dict:
    """
    Build a realistic Pub/Sub push notification payload for testing.

    Args:
        email_address: The watched Gmail address.
        history_id:    A fake Gmail history ID.
        message_id:    A fake Pub/Sub message ID.

    Returns:
        dict that parse_pubsub_notification() will accept.
    """
    import json as _json

    data_bytes = _json.dumps(
        {"emailAddress": email_address, "historyId": history_id}
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(data_bytes).decode("utf-8").rstrip("=")

    return {
        "message": {
            "data": encoded,
            "messageId": message_id,
            "publishTime": "2024-06-01T12:00:00.000Z",
        },
        "subscription": "projects/nexora-prod/subscriptions/gmail-push-sub",
    }
