"""
Customer Success Digital FTE - Main Agent (Stage 1 Prototype)

This module implements the core agent logic for the Customer Success Digital FTE.
It processes inbound customer messages, detects escalation triggers, searches the
knowledge base, and returns channel-appropriate formatted responses.

Stage 1: All logic is rule-based and self-contained. No external API calls.
Stage 2: This will be replaced with Claude API calls, real channel connectors,
         and database persistence.

Usage:
    python customer_success_agent.py
"""

from mcp_server import (
    search_kb,
    create_ticket,
    get_history,
    send_response,
    escalate_to_human,
)

# ---------------------------------------------------------------------------
# Escalation trigger definitions
# ---------------------------------------------------------------------------

ESCALATION_TRIGGERS: list[dict] = [
    {
        "reason": "legal_complaint",
        "severity": "high",
        "keywords": [
            "lawsuit", "legal action", "attorney", "lawyer", "sue",
            "litigation", "court", "file a complaint", "regulatory",
            "gdpr breach", "data breach", "legal",
        ],
    },
    {
        "reason": "security_issue",
        "severity": "critical",
        "keywords": [
            "hacked", "unauthorized access", "someone logged in",
            "stolen data", "privacy violation", "leak", "compromised",
            "breach", "security",
        ],
    },
    {
        "reason": "refund_request",
        "severity": "medium",
        "keywords": [
            "refund", "money back", "reimburse", "charge back",
            "return my money", "i want my money",
        ],
    },
    {
        "reason": "pricing_negotiation",
        "severity": "medium",
        "keywords": [
            "negotiate", "discount", "cheaper", "competitor price",
            "match price", "better deal", "reduce price", "lower rate",
            "25% cheaper", "20% cheaper",
        ],
    },
    {
        "reason": "angry_customer",
        "severity": "medium",
        "keywords": [
            "unacceptable", "outraged", "furious", "disgusting",
            "terrible", "worst", "pathetic", "i'm done", "fed up",
            "completely disappointed", "waste of money",
        ],
    },
]

VALID_CHANNELS = {"email", "whatsapp", "web_form"}

# ---------------------------------------------------------------------------
# Core agent logic
# ---------------------------------------------------------------------------

def check_escalation(message: str, customer: dict) -> dict | None:
    """
    Check if the message contains any escalation triggers.

    VIP/Enterprise customers are always escalated for complaints,
    regardless of keyword matches.

    Returns an escalation dict if triggered, None otherwise.
    """
    message_lower = message.lower()

    # Check VIP + complaint pattern first
    if customer.get("is_vip"):
        complaint_signals = [
            "issue", "problem", "wrong", "error", "broken", "not working",
            "cancel", "disappointed", "unhappy", "frustrated",
        ]
        if any(signal in message_lower for signal in complaint_signals):
            return {"reason": "vip_complaint", "severity": "high"}

    # Check keyword triggers
    for trigger in ESCALATION_TRIGGERS:
        if any(kw in message_lower for kw in trigger["keywords"]):
            return {"reason": trigger["reason"], "severity": trigger["severity"]}

    return None


def classify_intent(message: str) -> str:
    """
    Classify the broad intent of the message.
    Stage 1: Simple keyword heuristic.
    Stage 2: Claude API classification.
    """
    message_lower = message.lower()
    intent_map = [
        ("billing", ["invoice", "billing", "charge", "payment", "bill"]),
        ("account", ["login", "password", "locked", "access", "account"]),
        ("integration", ["slack", "google", "salesforce", "integration", "connect"]),
        ("plan", ["upgrade", "downgrade", "plan", "tier", "pricing"]),
        ("data", ["export", "download", "data", "backup"]),
        ("team", ["team", "invite", "user", "member", "add"]),
        ("cancellation", ["cancel", "cancellation", "unsubscribe"]),
        ("refund", ["refund", "money back", "reimburse"]),
        ("general", []),
    ]
    for intent, keywords in intent_map:
        if keywords and any(kw in message_lower for kw in keywords):
            return intent
    return "general"


def process_message(
    customer_id: str,
    channel: str,
    message: str,
) -> dict:
    """
    Main agent entry point. Processes one inbound customer message.

    Pipeline:
        1. Validate inputs
        2. Retrieve customer profile and history
        3. Check escalation triggers
        4. If escalation: create ticket + return escalation response
        5. If no escalation: search KB → format response → create ticket
        6. Return result dict

    Args:
        customer_id: Customer identifier.
        channel: One of 'email', 'whatsapp', 'web_form'.
        message: The raw customer message text.

    Returns:
        dict containing response, ticket info, escalation status, and metadata.
    """
    # Step 1: Validate channel
    if channel not in VALID_CHANNELS:
        return {
            "error": f"Unknown channel '{channel}'. Supported: {sorted(VALID_CHANNELS)}",
            "success": False,
        }

    # Step 2: Get customer context
    customer = get_history(customer_id)
    customer_name = customer.get("name", "Valued Customer")

    # Step 3: Classify intent (for logging and ticket subject)
    intent = classify_intent(message)

    # Step 4: Check escalation - ALWAYS before KB search
    escalation = check_escalation(message, customer)

    if escalation:
        # Create ticket with escalated status
        ticket = create_ticket(
            customer_id=customer_id,
            channel=channel,
            subject=f"[{intent.upper()}] {message[:60]}...",
            message=message,
            priority=escalation["severity"],
            status="escalated",
        )
        # Generate escalation holding response and flag for human
        escalation_result = escalate_to_human(
            ticket_id=ticket["ticket_id"],
            reason=escalation["reason"],
            severity=escalation["severity"],
            channel=channel,
            customer_name=customer_name,
        )
        return {
            "success": True,
            "escalated": True,
            "escalation_reason": escalation["reason"],
            "escalation_severity": escalation["severity"],
            "ticket": ticket,
            "response": escalation_result["holding_response"],
            "channel": channel,
            "customer": customer_name,
            "intent": intent,
            "kb_used": False,
        }

    # Step 5: Search knowledge base
    kb_result = search_kb(query=message)

    if kb_result["matched"]:
        # Use the top KB result as the response body
        top_match = kb_result["results"][0]
        response_body = top_match["content"]
        kb_topic = top_match["topic"]
    else:
        # No KB match - fallback response
        response_body = (
            "I don't have specific information about that in my current knowledge base. "
            "I've logged your query and will connect you with a specialist who can provide "
            "a detailed answer."
        )
        kb_topic = "no_match"

    # Step 6: Create ticket
    ticket = create_ticket(
        customer_id=customer_id,
        channel=channel,
        subject=f"[{intent.upper()}] {message[:60]}",
        message=message,
        priority="low",
        status="auto-resolved" if kb_result["matched"] else "pending_review",
    )

    # Step 7: Format and return response
    formatted = send_response(
        message_body=response_body,
        channel=channel,
        customer_name=customer_name,
        ticket_id=ticket["ticket_id"],
    )

    return {
        "success": True,
        "escalated": False,
        "ticket": ticket,
        "response": formatted["response"],
        "channel": channel,
        "customer": customer_name,
        "intent": intent,
        "kb_used": kb_result["matched"],
        "kb_topic": kb_topic,
    }


# ---------------------------------------------------------------------------
# Demo runner - shows the agent processing sample messages
# ---------------------------------------------------------------------------

DEMO_MESSAGES = [
    {
        "label": "Routine - Password Reset (Email)",
        "customer_id": "CUST-001",
        "channel": "email",
        "message": "Hi, I've forgotten my password and I'm locked out of my account. How do I reset it?",
    },
    {
        "label": "Routine - Invoice Question (WhatsApp)",
        "customer_id": "CUST-002",
        "channel": "whatsapp",
        "message": "Hi, I need my invoice for last month please",
    },
    {
        "label": "Escalation - Refund Request (Web Form)",
        "customer_id": "CUST-003",
        "channel": "web_form",
        "message": "We signed up last week but the product doesn't work for us. I need a full refund.",
    },
    {
        "label": "Escalation - Angry Customer (Email)",
        "customer_id": "CUST-004",
        "channel": "email",
        "message": "This is completely unacceptable. I've been waiting three weeks for a fix. Worst support I've ever experienced.",
    },
    {
        "label": "Escalation - Legal Threat (Email)",
        "customer_id": "CUST-001",
        "channel": "email",
        "message": "If this is not resolved immediately I will consult with my attorney and consider legal action.",
    },
    {
        "label": "VIP Complaint - Enterprise Customer (WhatsApp)",
        "customer_id": "CUST-005",
        "channel": "whatsapp",
        "message": "We're really disappointed with the SSO integration. It's been broken for days and nothing is getting fixed.",
    },
    {
        "label": "Routine - Slack Integration (Web Form)",
        "customer_id": "CUST-002",
        "channel": "web_form",
        "message": "How do I connect my Slack workspace to Nexora?",
    },
    {
        "label": "No KB Match - Unknown Topic (Email)",
        "customer_id": "CUST-001",
        "channel": "email",
        "message": "I'm looking for information about your API rate limits and webhook documentation.",
    },
]


def run_demo():
    """Run the agent against all demo messages and print formatted results."""
    separator = "=" * 70

    print(separator)
    print("  CUSTOMER SUCCESS DIGITAL FTE - Stage 1 Prototype Demo")
    print("  Hackathon 5 | Author: Mehreen Asghar")
    print(separator)

    for i, demo in enumerate(DEMO_MESSAGES, 1):
        print(f"\n[{i}/{len(DEMO_MESSAGES)}] {demo['label']}")
        print(f"  Customer: {demo['customer_id']}  |  Channel: {demo['channel'].upper()}")
        print(f"  Message: \"{demo['message'][:80]}{'...' if len(demo['message']) > 80 else ''}\"")
        print()

        result = process_message(
            customer_id=demo["customer_id"],
            channel=demo["channel"],
            message=demo["message"],
        )

        if not result.get("success"):
            print(f"  ERROR: {result.get('error')}")
            continue

        # Status line
        if result["escalated"]:
            print(f"  STATUS: ESCALATED [{result['escalation_severity'].upper()}]")
            print(f"  REASON: {result['escalation_reason'].replace('_', ' ').title()}")
        else:
            print(f"  STATUS: AUTO-RESPONDED | KB topic: {result.get('kb_topic', 'N/A')}")

        print(f"  TICKET: {result['ticket']['ticket_id']} ({result['ticket']['status']})")
        print()
        print("  --- RESPONSE ---")
        # Indent response lines for readability
        for line in result["response"].split("\n"):
            print(f"  {line}")
        print(separator)


if __name__ == "__main__":
    run_demo()
