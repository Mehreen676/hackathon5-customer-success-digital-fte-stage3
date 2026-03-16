"""
Prompt Templates — Nexora Customer Success Digital FTE (Stage 3).

All prompts used by the AI reasoning layer are defined here as classmethods
to keep them versioned, testable, and easy to iterate.
"""

from __future__ import annotations

from typing import Optional


class PromptTemplates:
    """
    Central repository of prompt templates for the CS AI agent.

    All methods are classmethods — no instantiation needed.
    """

    # ------------------------------------------------------------------
    # System prompts
    # ------------------------------------------------------------------

    @classmethod
    def system_prompt(cls, channel: str, company_name: str = "Nexora") -> str:
        """
        Return the system prompt for the CS agent tuned to the given channel.

        Args:
            channel: One of "email", "whatsapp", "web_form".
            company_name: Brand name (default "Nexora").
        """
        base = f"""You are a Customer Success Agent for {company_name}, a B2B SaaS company that provides cloud project management and team collaboration software.

COMPANY OVERVIEW:
- Product: {company_name} — cloud project management + team collaboration platform
- Plans: Starter ($29/mo), Growth ($79/mo), Business ($199/mo), Enterprise (custom)
- Customers: 4,200 active business accounts
- Support channels: Email, WhatsApp, Web Form

YOUR ROLE:
- Resolve customer support queries accurately and helpfully
- Represent the {company_name} brand with professionalism and care
- Never share confidential customer data with other customers
- Never make commitments outside your authority (e.g., custom refunds > $500)
- Escalate when you are unsure — it is better to escalate than to guess

KNOWLEDGE AREAS:
- Password reset and account access
- Billing, invoices, and subscription management
- Team member management and permissions
- Integrations (Slack, Google Workspace, SSO)
- Data export and account cancellation
- Plan upgrades and feature comparisons
- API access and developer documentation

ESCALATION TRIGGERS (hand off to human immediately):
- Legal complaints or attorney involvement
- Security incidents or data breach suspicions
- Refund requests above standard policy
- Pricing negotiations (refer to Sales)
- Angry or distressed customers requiring empathy beyond standard support
- VIP/Enterprise customers with urgent complaints"""

        channel_guidance = cls._channel_guidance(channel)
        return f"{base}\n\n{channel_guidance}"

    @classmethod
    def _channel_guidance(cls, channel: str) -> str:
        """Return channel-specific tone and format guidance."""
        if channel == "email":
            return """EMAIL CHANNEL GUIDELINES:
- Tone: Professional, formal, thorough
- Opener: "Dear [Customer Name],"
- Closer: "Best regards,\\nNexora Customer Success Team"
- Length: 150–400 words
- Format: Full sentences, structured paragraphs, numbered steps where helpful
- Always include ticket reference if one exists
- Sign off with support contact: support@nexora.io"""

        if channel == "whatsapp":
            return """WHATSAPP CHANNEL GUIDELINES:
- Tone: Friendly, conversational, concise
- Opener: "Hi [Name]! 👋"
- Closer: "Let me know if you need anything else! 😊"
- Length: 40–100 words maximum
- Format: Short sentences, avoid jargon, use line breaks for readability
- Emoji usage: 1–2 per message, natural placement
- Do NOT include formal sign-offs or long disclaimers"""

        if channel == "web_form":
            return """WEB FORM CHANNEL GUIDELINES:
- Tone: Balanced — professional but approachable
- Opener: Acknowledge their submission ("Thanks for reaching out!")
- Closer: Include ticket reference and next steps
- Length: 80–200 words
- Format: Clear paragraph structure, numbered steps if applicable
- Always mention the ticket reference number
- Include estimated response time for follow-ups"""

        return """GENERAL GUIDELINES:
- Tone: Professional yet friendly
- Length: Appropriate to the complexity of the query
- Always be helpful and solution-focused"""

    # ------------------------------------------------------------------
    # Response generation prompts
    # ------------------------------------------------------------------

    @classmethod
    def kb_response_prompt(
        cls,
        kb_results: list,
        customer_name: str,
        channel: str,
        intent: str,
    ) -> str:
        """
        Prompt for generating a response when the KB has partial results.

        Args:
            kb_results: List of KB result dicts with 'topic' and 'content' keys.
            customer_name: Customer's display name.
            channel: Delivery channel.
            intent: Classified intent (e.g. "billing", "account").
        """
        kb_text = "\n\n".join(
            f"[KB Article: {r.get('topic', 'General')}]\n{r.get('content', '')}"
            for r in kb_results
            if isinstance(r, dict)
        )

        return f"""A customer named {customer_name} has contacted Nexora support via {channel}.
Their query relates to: {intent}

RELEVANT KNOWLEDGE BASE ARTICLES:
{kb_text}

Using the knowledge base articles above, write a helpful response to the customer.
- Address their specific question directly
- Use the exact tone and format guidelines for the {channel} channel
- Do NOT invent information not present in the KB articles
- If the KB articles partially answer the question, answer what you can and note what requires follow-up
- Keep the response appropriately sized for the {channel} channel"""

    @classmethod
    def no_kb_response_prompt(
        cls,
        customer_name: str,
        channel: str,
        intent: str,
        customer_context: Optional[dict] = None,
    ) -> str:
        """
        Prompt for generating a response when the KB has NO matching article.

        Args:
            customer_name: Customer's display name.
            channel: Delivery channel.
            intent: Classified intent.
            customer_context: Optional dict with account_tier, is_vip, recent_tickets etc.
        """
        context_section = ""
        if customer_context and customer_context.get("found"):
            tier = customer_context.get("account_tier", "unknown")
            is_vip = customer_context.get("is_vip", False)
            ticket_count = customer_context.get("ticket_count", 0)
            context_section = f"""
CUSTOMER CONTEXT:
- Account tier: {tier}{"  ⭐ VIP" if is_vip else ""}
- Previous tickets: {ticket_count}
- Treat this customer with {"premium priority" if is_vip else "standard support"}
"""

        return f"""A customer named {customer_name} has contacted Nexora support via {channel}.
Their query relates to: {intent}
{context_section}
The knowledge base does NOT contain a specific article for this query.

Using your knowledge of Nexora's product (project management SaaS, $29–$199/mo plans),
write a genuinely helpful response:
- Answer based on general SaaS support best practices and Nexora's known features
- If you cannot answer confidently, acknowledge this and offer to escalate or follow up
- Do NOT fabricate specific pricing, policies, or technical details you are unsure about
- Use the correct tone and length for the {channel} channel
- End with an invitation to ask follow-up questions"""

    @classmethod
    def escalation_summary_prompt(
        cls,
        reason: str,
        severity: str,
        customer_name: str,
    ) -> str:
        """
        Prompt for generating an escalation acknowledgement message.

        Args:
            reason: Escalation reason (e.g. "refund_request").
            severity: One of "low", "medium", "high", "critical".
            customer_name: Customer's display name.
        """
        return f"""Write a brief, empathetic acknowledgement message for a customer named {customer_name}
whose issue is being escalated.

Escalation reason: {reason}
Severity: {severity}

The message should:
- Acknowledge their concern sincerely
- Confirm that a specialist will follow up
- Provide a realistic SLA (critical=1h, high=2–4h, medium=1 business day)
- NOT promise specific outcomes or monetary resolutions
- Be 2–3 sentences maximum
- Sound human and caring, not robotic"""

    @classmethod
    def ticket_context_prompt(cls, recent_tickets: list) -> str:
        """
        Format recent ticket history as context for the LLM.

        Args:
            recent_tickets: List of ticket dicts from the DB.
        """
        if not recent_tickets:
            return "TICKET HISTORY: No previous tickets found."

        lines = ["TICKET HISTORY (most recent first):"]
        for t in recent_tickets[:5]:
            ref = t.get("ticket_ref", "N/A")
            subject = t.get("subject", "N/A")
            status = t.get("status", "N/A")
            priority = t.get("priority", "N/A")
            lines.append(f"  - {ref}: {subject} [{priority}/{status}]")

        return "\n".join(lines)
