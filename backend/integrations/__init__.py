"""
Integrations — Customer Success Digital FTE (Stage 3)

External service clients:
    gmail_client    Google Gmail API (send + fetch), MOCK mode when unconfigured
    twilio_client   Twilio WhatsApp API (send), MOCK mode when unconfigured
"""

from backend.integrations.gmail_client import GmailClient, gmail_client
from backend.integrations.twilio_client import TwilioClient, twilio_client

__all__ = ["GmailClient", "gmail_client", "TwilioClient", "twilio_client"]
