"""
MCP Server - Customer Success Digital FTE (Stage 1 Prototype)

Defines the five core MCP tools used by the customer success agent.
In Stage 1 these are plain Python functions with a consistent interface.
In Stage 2 these will be exposed via the MCP protocol and called by Claude.

Tools:
    search_kb           - Search local knowledge base for relevant content
    create_ticket       - Create a support ticket in-memory
    get_history         - Retrieve customer interaction history
    send_response       - Format and return a channel-specific response
    escalate_to_human   - Flag ticket for human agent review
"""

import uuid
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# In-memory stores (Stage 1 only - replaced by PostgreSQL in Stage 2)
# ---------------------------------------------------------------------------

TICKET_STORE: dict = {}

CUSTOMER_STORE: dict = {
    "CUST-001": {
        "name": "Sarah Mitchell",
        "email": "sarah.mitchell@brightflow.com",
        "account_tier": "Growth",
        "is_vip": False,
        "tickets": ["TKT-0001"],
    },
    "CUST-002": {
        "name": "James Okafor",
        "email": "james.okafor@deltaops.io",
        "account_tier": "Starter",
        "is_vip": False,
        "tickets": ["TKT-0002"],
    },
    "CUST-003": {
        "name": "Priya Sharma",
        "email": "priya@techbridge.net",
        "account_tier": "Business",
        "is_vip": False,
        "tickets": ["TKT-0003"],
    },
    "CUST-004": {
        "name": "Daniel Cruz",
        "email": "d.cruz@constructly.com",
        "account_tier": "Growth",
        "is_vip": False,
        "tickets": ["TKT-0004"],
    },
    "CUST-005": {
        "name": "Amara Diallo",
        "email": "amara.diallo@lunarcorp.io",
        "account_tier": "Enterprise",
        "is_vip": True,
        "tickets": ["TKT-0005"],
    },
}

# Flat knowledge base content (keyword-searchable in Stage 1)
KNOWLEDGE_BASE: list[dict] = [
    {
        "topic": "password_reset",
        "keywords": ["password", "reset", "login", "locked", "access", "forgot"],
        "content": (
            "To reset your password: go to nexora.io/login, click 'Forgot password', "
            "enter your email, then check your inbox for a reset link. "
            "The link expires in 30 minutes. "
            "After 5 failed login attempts, your account is locked for 15 minutes."
        ),
    },
    {
        "topic": "billing_invoice",
        "keywords": ["invoice", "billing", "receipt", "payment", "charge", "bill"],
        "content": (
            "Invoices are available in Settings > Billing > Invoices. "
            "You can download PDF invoices for all past payments. "
            "Your billing date is the same day of the month you originally subscribed."
        ),
    },
    {
        "topic": "add_team_member",
        "keywords": ["add", "invite", "team", "member", "user", "colleague", "new user"],
        "content": (
            "To add a team member: go to Settings > Team Members > Invite User. "
            "Enter their email and choose their role (Viewer, Editor, or Admin). "
            "They will receive an email invitation to join your workspace."
        ),
    },
    {
        "topic": "slack_integration",
        "keywords": ["slack", "integration", "connect", "integrate", "notification"],
        "content": (
            "To connect Slack: go to Settings > Integrations > Slack > Connect. "
            "You will be prompted to authorize the Nexora Slack app in your workspace. "
            "Once connected, you can receive task notifications directly in Slack."
        ),
    },
    {
        "topic": "plan_upgrade",
        "keywords": ["upgrade", "plan", "tier", "pricing", "starter", "growth", "business", "enterprise"],
        "content": (
            "To upgrade your plan: go to Settings > Billing > Plan > Upgrade. "
            "Changes are immediate and you will be charged a prorated amount. "
            "Plans available: Starter ($29/mo), Growth ($79/mo), Business ($199/mo), Enterprise (custom). "
            "Annual billing saves 20%."
        ),
    },
    {
        "topic": "refund_policy",
        "keywords": ["refund", "money back", "return", "cancel", "reimburse"],
        "content": (
            "Nexora offers refunds within 14 days of the initial purchase or renewal for annual plans. "
            "Monthly plans are non-refundable after the billing date. "
            "All refund requests are reviewed by the billing team within 1 business day."
        ),
    },
    {
        "topic": "cancellation",
        "keywords": ["cancel", "cancellation", "unsubscribe", "stop", "end subscription"],
        "content": (
            "To cancel your subscription: go to Settings > Billing > Plan > Cancel Subscription. "
            "Your account remains active until the end of the current billing period. "
            "You can reactivate at any time."
        ),
    },
    {
        "topic": "data_export",
        "keywords": ["export", "download", "data", "backup", "extract"],
        "content": (
            "To export your data: go to Settings > Data > Export. "
            "You can export all projects, tasks, and documents as a ZIP file. "
            "Export requests are processed within 24 hours."
        ),
    },
    {
        "topic": "sso_setup",
        "keywords": ["sso", "single sign-on", "saml", "okta", "identity", "login"],
        "content": (
            "SSO is available on Business and Enterprise plans only. "
            "Setup: go to Settings > Security > SSO and follow the SAML 2.0 guide. "
            "For Enterprise SSO setup, contact your dedicated account manager."
        ),
    },
]

# ---------------------------------------------------------------------------
# Response style templates per channel
# ---------------------------------------------------------------------------

CHANNEL_STYLES: dict = {
    "email": {
        "opener": "Dear {name},\n\nThank you for contacting Nexora Customer Success.",
        "closer": "\n\nPlease don't hesitate to reach out if you need further assistance.\n\nBest regards,\nNexora Customer Success Team",
        "max_words": 400,
        "formal": True,
    },
    "whatsapp": {
        "opener": "Hi {name}!",
        "closer": " Let me know if that helps!",
        "max_words": 80,
        "formal": False,
    },
    "web_form": {
        "opener": "Thanks for reaching out to Nexora Support.",
        "closer": "\n\nIf you need anything else, reply to this message or contact us at support@nexora.io",
        "max_words": 200,
        "formal": False,
    },
}

ESCALATION_RESPONSES: dict = {
    "email": (
        "Dear {name},\n\n"
        "Thank you for reaching out. I've reviewed your message and I want to make sure "
        "you receive the best possible support for your situation.\n\n"
        "I've escalated your case to our {team} team with {severity} priority. "
        "A team member will be in contact with you within {sla}.\n\n"
        "Reference: {ticket_id}\n\n"
        "Best regards,\nNexora Customer Success Team"
    ),
    "whatsapp": (
        "Hi {name}! I've flagged your message for our {team} team - "
        "someone will reach out within {sla}. Reference: {ticket_id}"
    ),
    "web_form": (
        "Thanks for reaching out. I've escalated your case to our {team} team ({severity} priority).\n\n"
        "A team member will contact you within {sla}.\n\n"
        "Reference: {ticket_id}"
    ),
}

SLA_BY_SEVERITY: dict = {
    "critical": "2 hours",
    "high": "2 hours",
    "medium": "1 business day",
    "low": "2 business days",
}

TEAM_BY_REASON: dict = {
    "refund_request": "Billing",
    "pricing_negotiation": "Sales & Account Management",
    "legal_complaint": "Legal & Customer Success",
    "angry_customer": "Senior Customer Success",
    "vip_complaint": "Account Management",
    "security_issue": "Security",
}


# ---------------------------------------------------------------------------
# Tool 1: search_kb
# ---------------------------------------------------------------------------

def search_kb(query: str, max_results: int = 3) -> dict:
    """
    Search the local knowledge base for content relevant to the query.

    Args:
        query: The customer's question or keywords to search for.
        max_results: Maximum number of KB entries to return.

    Returns:
        dict with 'results' (list of matching entries) and 'matched' (bool).
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())

    scored_results = []
    for entry in KNOWLEDGE_BASE:
        # Count how many KB keywords appear in the query
        match_score = sum(1 for kw in entry["keywords"] if kw in query_lower)
        # Also check partial word overlap
        keyword_words = set(" ".join(entry["keywords"]).split())
        word_overlap = len(query_words & keyword_words)
        total_score = match_score + (word_overlap * 0.5)

        if total_score > 0:
            scored_results.append((total_score, entry))

    scored_results.sort(key=lambda x: x[0], reverse=True)
    top_results = [entry for _, entry in scored_results[:max_results]]

    return {
        "matched": len(top_results) > 0,
        "results": top_results,
        "query": query,
    }


# ---------------------------------------------------------------------------
# Tool 2: create_ticket
# ---------------------------------------------------------------------------

def create_ticket(
    customer_id: str,
    channel: str,
    subject: str,
    message: str,
    priority: str = "low",
    status: str = "open",
) -> dict:
    """
    Create a support ticket in the in-memory ticket store.

    Args:
        customer_id: The customer's ID.
        channel: Channel the ticket came through (email/whatsapp/web_form).
        subject: Brief subject line for the ticket.
        message: The original customer message.
        priority: Ticket priority - low / medium / high / critical.
        status: Initial status - open / escalated / auto-resolved.

    Returns:
        dict with ticket_id, status, created_at.
    """
    ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
    ticket = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "channel": channel,
        "subject": subject,
        "message": message,
        "priority": priority,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "escalated": status == "escalated",
    }
    TICKET_STORE[ticket_id] = ticket
    return {
        "ticket_id": ticket_id,
        "status": status,
        "priority": priority,
        "created_at": ticket["created_at"],
    }


# ---------------------------------------------------------------------------
# Tool 3: get_history
# ---------------------------------------------------------------------------

def get_history(customer_id: str) -> dict:
    """
    Retrieve a customer's profile and past interaction history.

    Args:
        customer_id: The customer's ID.

    Returns:
        dict with customer profile and list of past ticket IDs.
        If customer is not found, returns a guest profile.
    """
    if customer_id in CUSTOMER_STORE:
        customer = CUSTOMER_STORE[customer_id].copy()
        # Look up any tickets we've created this session
        session_tickets = [
            t for t in TICKET_STORE.values()
            if t["customer_id"] == customer_id
        ]
        customer["session_tickets"] = session_tickets
        customer["found"] = True
        return customer

    # Guest profile for unknown customers
    return {
        "found": False,
        "name": "Valued Customer",
        "email": None,
        "account_tier": "unknown",
        "is_vip": False,
        "tickets": [],
        "session_tickets": [],
    }


# ---------------------------------------------------------------------------
# Tool 4: send_response
# ---------------------------------------------------------------------------

def send_response(
    message_body: str,
    channel: str,
    customer_name: str,
    ticket_id: str = "",
) -> dict:
    """
    Format a response for the specified channel and return it.

    Args:
        message_body: The core answer/response text.
        channel: Target channel - email / whatsapp / web_form.
        customer_name: Customer's first name (for salutation).
        ticket_id: Optional ticket reference to include in the response.

    Returns:
        dict with 'response' (formatted string) and 'channel'.
    """
    style = CHANNEL_STYLES.get(channel, CHANNEL_STYLES["web_form"])
    first_name = customer_name.split()[0] if customer_name else "there"

    opener = style["opener"].format(name=first_name)
    closer = style["closer"]

    if channel == "email":
        body = f"{opener}\n\n{message_body}"
        if ticket_id:
            body += f"\n\nReference: {ticket_id}"
        body += closer
    elif channel == "whatsapp":
        # Keep it short - truncate if needed
        words = message_body.split()
        if len(words) > style["max_words"]:
            message_body = " ".join(words[:style["max_words"]]) + "..."
        body = f"{opener} {message_body}{closer}"
    else:  # web_form
        body = f"{opener}\n\n{message_body}"
        if ticket_id:
            body += f"\n\nReference: {ticket_id}"
        body += closer

    return {
        "response": body,
        "channel": channel,
        "delivered": True,  # Simulated - no real send in Stage 1
    }


# ---------------------------------------------------------------------------
# Tool 5: escalate_to_human
# ---------------------------------------------------------------------------

def escalate_to_human(
    ticket_id: str,
    reason: str,
    severity: str,
    channel: str,
    customer_name: str,
) -> dict:
    """
    Flag a ticket for human agent review and generate a holding response.

    Args:
        ticket_id: The ticket to escalate.
        reason: Escalation reason key (e.g. 'refund_request', 'legal_complaint').
        severity: Severity level - low / medium / high / critical.
        channel: Channel to send the holding response through.
        customer_name: Customer's name for the holding response.

    Returns:
        dict with escalation confirmation and the holding response to send.
    """
    # Update ticket status in store
    if ticket_id in TICKET_STORE:
        TICKET_STORE[ticket_id]["status"] = "escalated"
        TICKET_STORE[ticket_id]["escalated"] = True
        TICKET_STORE[ticket_id]["escalation_reason"] = reason
        TICKET_STORE[ticket_id]["escalation_severity"] = severity

    team = TEAM_BY_REASON.get(reason, "Customer Success")
    sla = SLA_BY_SEVERITY.get(severity, "1 business day")
    first_name = customer_name.split()[0] if customer_name else "there"

    template = ESCALATION_RESPONSES.get(channel, ESCALATION_RESPONSES["web_form"])
    holding_response = template.format(
        name=first_name,
        team=team,
        severity=severity,
        sla=sla,
        ticket_id=ticket_id,
    )

    # In Stage 2: send Slack notification to human agent here
    # notification_service.notify(team=team, ticket_id=ticket_id, severity=severity)

    return {
        "escalated": True,
        "ticket_id": ticket_id,
        "assigned_team": team,
        "severity": severity,
        "sla": sla,
        "holding_response": holding_response,
        "notification_sent": False,  # Simulated in Stage 1
    }
