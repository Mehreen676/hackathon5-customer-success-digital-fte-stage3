"""
Webhooks — Customer Success Digital FTE (Stage 3)

Parsing helpers for inbound webhooks from external services:
    gmail_webhook       Google Cloud Pub/Sub push notifications
    whatsapp_webhook    Twilio WhatsApp form-encoded payloads
"""

from backend.webhooks.gmail_webhook import parse_pubsub_notification, extract_sender_info
from backend.webhooks.whatsapp_webhook import parse_twilio_webhook, validate_twilio_signature

__all__ = [
    "parse_pubsub_notification",
    "extract_sender_info",
    "parse_twilio_webhook",
    "validate_twilio_signature",
]
