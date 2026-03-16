"""
Web Form Channel Handler — Customer Success Digital FTE (Stage 2)

Normalizes inbound web support form submissions to the unified
NormalizedMessage format understood by the agent workflow.

Stage 2: Form normalization only.
Stage 3: Real-time form webhooks and CRM integration.
"""

import logging

from backend.schemas.message_schema import NormalizedMessage, WebFormRequest

logger = logging.getLogger(__name__)


class WebFormHandler:
    """
    Handles web support form submissions.

    Converts WebFormRequest → NormalizedMessage.
    Responses are structured and balanced (web form style).
    """

    channel = "web_form"

    def normalize(self, payload: WebFormRequest) -> NormalizedMessage:
        """
        Normalize a web form submission into the unified message format.

        Customer ID strategy:
          1. Use explicitly provided customer_id if set.
          2. Fall back to email-prefixed identifier (email:{email}).

        The subject line is prepended to the message body to provide
        additional context for KB search and intent classification.

        Args:
            payload: Validated WebFormRequest from the API endpoint.

        Returns:
            NormalizedMessage ready for the agent workflow.
        """
        customer_id = payload.customer_id.strip()
        if not customer_id:
            customer_id = f"email:{payload.email}"

        # Combine subject + message for richer context
        full_content = payload.message.strip()
        if payload.subject and payload.subject not in full_content:
            full_content = f"Subject: {payload.subject}\n\n{payload.message.strip()}"

        logger.info(
            "Web form handler normalizing submission from %s | subject: %s",
            payload.email,
            payload.subject[:50],
        )

        return NormalizedMessage(
            customer_id=customer_id,
            channel=self.channel,
            content=full_content,
            customer_name=payload.name,
            customer_email=payload.email,
            metadata={
                "from_email": payload.email,
                "from_name": payload.name,
                "subject": payload.subject,
                "source_channel": "web_form",
            },
        )

    def format_response(self, response_text: str) -> dict:
        """
        Wrap the agent response in a web form delivery envelope.

        Stage 2: Returns response text with delivery metadata.
        Stage 3: Sends email confirmation + stores in CRM.
        """
        return {
            "channel": self.channel,
            "formatted_response": response_text,
            "delivery_method": "email_confirmation",
            "delivered": False,  # Stage 3: real delivery
        }


# Module-level instance for convenience
webform_handler = WebFormHandler()
