"""
Gmail Channel Handler — Customer Success Digital FTE (Stage 2)

Normalizes inbound Gmail webhook payloads to the unified NormalizedMessage
format understood by the agent workflow.

Stage 2: Payload normalization only.
Stage 3: Real Gmail API OAuth2 + push notifications.
"""

import logging

from backend.schemas.message_schema import GmailMessageRequest, NormalizedMessage

logger = logging.getLogger(__name__)


class GmailHandler:
    """
    Handles Gmail channel messages.

    Converts GmailMessageRequest → NormalizedMessage for the agent workflow.
    """

    channel = "email"

    def normalize(self, payload: GmailMessageRequest) -> NormalizedMessage:
        """
        Normalize a Gmail payload into the unified message format.

        Customer ID strategy:
          1. Use explicitly provided customer_id if set.
          2. Fall back to email-prefixed identifier (email:{from_email}).

        Args:
            payload: Validated GmailMessageRequest from the API endpoint.

        Returns:
            NormalizedMessage ready for the agent workflow.
        """
        # Determine customer identifier
        customer_id = payload.customer_id.strip()
        if not customer_id:
            customer_id = f"email:{payload.from_email}"

        # Combine subject + body for richer KB search context
        full_content = payload.body.strip()
        if payload.subject and payload.subject not in full_content:
            full_content = f"{payload.subject}\n\n{payload.body.strip()}"

        customer_name = payload.from_name.strip() if payload.from_name else payload.from_email.split("@")[0].title()

        logger.info(
            "Gmail handler normalizing message from %s | subject: %s",
            payload.from_email,
            payload.subject[:50],
        )

        return NormalizedMessage(
            customer_id=customer_id,
            channel=self.channel,
            content=full_content,
            customer_name=customer_name,
            customer_email=payload.from_email,
            metadata={
                "from_email": payload.from_email,
                "from_name": payload.from_name,
                "subject": payload.subject,
                "source_channel": "gmail",
            },
        )

    def format_response(self, response_text: str) -> dict:
        """
        Wrap the agent response in a Gmail-style delivery envelope.

        Stage 2: Returns metadata only (no real send).
        Stage 3: Calls Gmail API to send the reply thread.
        """
        return {
            "channel": self.channel,
            "formatted_response": response_text,
            "delivery_method": "gmail_api",
            "delivered": False,  # Stage 3: real delivery
        }


# Module-level instance for convenience
gmail_handler = GmailHandler()
