"""
MCP Tool: send_channel_response

Formats a response body according to the channel's style guidelines
and returns the formatted response string.

Stage 2: Formatting logic — no live sending (webhook delivery is Stage 3).

Registered as: "send_channel_response"
"""

import logging

from backend.mcp.tool_registry import register

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Channel style definitions — mirrors and extends Stage 1 CHANNEL_STYLES
# ---------------------------------------------------------------------------

CHANNEL_STYLES: dict[str, dict] = {
    "email": {
        "opener": "Dear {name},\n\nThank you for contacting Nexora Customer Success.",
        "closer": (
            "\n\nPlease don't hesitate to reach out if you need further assistance.\n\n"
            "Best regards,\nNexora Customer Success Team"
        ),
        "max_words": 400,
        "formal": True,
    },
    "whatsapp": {
        "opener": "Hi {name}!",
        "closer": " Let me know if that helps! 👍",
        "max_words": 80,
        "formal": False,
    },
    "web_form": {
        "opener": "Thanks for reaching out to Nexora Support.",
        "closer": (
            "\n\nIf you need anything else, reply to this message "
            "or contact us at support@nexora.io"
        ),
        "max_words": 200,
        "formal": False,
    },
}


@register("send_channel_response")
def send_channel_response(
    message_body: str,
    channel: str,
    customer_name: str,
    ticket_ref: str = "",
) -> dict:
    """
    Format a support response for the specified channel.

    Args:
        message_body: The core answer / response text.
        channel: email | whatsapp | web_form
        customer_name: Customer's full name (first name used for salutations).
        ticket_ref: Optional ticket reference to include in the response.

    Returns:
        dict:
            response (str)   — Fully formatted response text
            channel (str)    — The target channel
            delivered (bool) — Always False in Stage 2; Stage 3 adds webhooks
    """
    style = CHANNEL_STYLES.get(channel, CHANNEL_STYLES["web_form"])
    first_name = customer_name.split()[0] if customer_name else "there"

    opener = style["opener"].format(name=first_name)
    closer = style["closer"]

    if channel == "email":
        body = f"{opener}\n\n{message_body}"
        if ticket_ref:
            body += f"\n\nReference: {ticket_ref}"
        body += closer

    elif channel == "whatsapp":
        # Keep WhatsApp responses concise
        words = message_body.split()
        if len(words) > style["max_words"]:
            message_body = " ".join(words[: style["max_words"]]) + "..."
        body = f"{opener} {message_body}{closer}"
        if ticket_ref:
            body += f" (Ref: {ticket_ref})"

    else:  # web_form (default)
        body = f"{opener}\n\n{message_body}"
        if ticket_ref:
            body += f"\n\nReference: {ticket_ref}"
        body += closer

    logger.info(
        "Formatted response for channel=%s | words=%d | ticket=%s",
        channel, len(body.split()), ticket_ref or "none"
    )

    return {
        "response": body,
        "channel": channel,
        "delivered": False,  # Stage 3: real channel delivery
    }
