"""
Message Schemas — inbound message request models (Stage 2)
"""

from pydantic import BaseModel, Field


class GenericMessageRequest(BaseModel):
    """Unified message format accepted by POST /support/message."""

    customer_id: str = Field(..., description="Customer external ID (e.g. CUST-001)")
    channel: str = Field(..., description="Channel: email | whatsapp | web_form")
    content: str = Field(..., min_length=1, description="Message body text")
    metadata: dict = Field(default_factory=dict, description="Optional channel metadata")


class GmailMessageRequest(BaseModel):
    """Payload structure for POST /support/gmail (simulated Gmail webhook)."""

    from_email: str = Field(..., description="Sender email address")
    from_name: str = Field(default="", description="Sender display name")
    subject: str = Field(default="Support Request", description="Email subject line")
    body: str = Field(..., min_length=1, description="Email body text")
    customer_id: str = Field(default="", description="Optional known customer ID")


class WhatsAppMessageRequest(BaseModel):
    """Payload structure for POST /support/whatsapp (simulated WhatsApp Business webhook)."""

    from_phone: str = Field(..., description="Sender phone number in E.164 format")
    message_text: str = Field(..., min_length=1, description="Message body text")
    customer_id: str = Field(default="", description="Optional known customer ID")


class WebFormRequest(BaseModel):
    """Payload structure for POST /support/webform (web support form submission)."""

    name: str = Field(..., description="Submitter full name")
    email: str = Field(..., description="Submitter email address")
    subject: str = Field(default="Support Request", description="Form subject")
    message: str = Field(..., min_length=1, description="Message body")
    customer_id: str = Field(default="", description="Optional known customer ID")


class NormalizedMessage(BaseModel):
    """Internal normalized format passed to the agent workflow."""

    customer_id: str
    channel: str
    content: str
    customer_name: str = "Valued Customer"
    customer_email: str | None = None
    metadata: dict = Field(default_factory=dict)
