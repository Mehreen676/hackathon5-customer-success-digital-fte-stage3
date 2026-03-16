"""
WhatsApp Channel Handler — Customer Success Digital FTE (Stage 2)

Normalizes inbound WhatsApp Business webhook payloads to the unified
NormalizedMessage format understood by the agent workflow.

Stage 2: Payload normalization only.
Stage 3: Real Twilio WhatsApp API integration.
"""

import logging

from backend.schemas.message_schema import NormalizedMessage, WhatsAppMessageRequest

logger = logging.getLogger(__name__)


class WhatsAppHandler:
    """
    Handles WhatsApp Business channel messages.

    Converts WhatsAppMessageRequest → NormalizedMessage.
    Responses are kept short and conversational (WhatsApp style).
    """

    channel = "whatsapp"

    def normalize(self, payload: WhatsAppMessageRequest) -> NormalizedMessage:
        """
        Normalize a WhatsApp message payload into the unified format.

        Customer ID strategy:
          1. Use explicitly provided customer_id if set.
          2. Fall back to phone-prefixed identifier (phone:{from_phone}).

        Args:
            payload: Validated WhatsAppMessageRequest from the API endpoint.

        Returns:
            NormalizedMessage ready for the agent workflow.
        """
        customer_id = payload.customer_id.strip()
        if not customer_id:
            customer_id = f"phone:{payload.from_phone}"

        # Derive a display name from the phone number if no name available
        customer_name = f"WhatsApp User ({payload.from_phone[-4:]})"

        logger.info(
            "WhatsApp handler normalizing message from %s | length=%d",
            payload.from_phone,
            len(payload.message_text),
        )

        return NormalizedMessage(
            customer_id=customer_id,
            channel=self.channel,
            content=payload.message_text.strip(),
            customer_name=customer_name,
            customer_email=None,
            metadata={
                "from_phone": payload.from_phone,
                "source_channel": "whatsapp_business",
            },
        )

    def format_response(self, response_text: str) -> dict:
        """
        Wrap the agent response in a WhatsApp delivery envelope.

        Stage 2: Returns metadata only.
        Stage 3: Calls Twilio API to send the WhatsApp message.
        """
        return {
            "channel": self.channel,
            "formatted_response": response_text,
            "delivery_method": "twilio_whatsapp",
            "delivered": False,  # Stage 3: real delivery
        }


# Module-level instance for convenience
whatsapp_handler = WhatsAppHandler()
