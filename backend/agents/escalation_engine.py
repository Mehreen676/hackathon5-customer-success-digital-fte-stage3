"""
Escalation Engine — Customer Success Digital FTE (Stage 2)

Detects whether an inbound customer message requires human escalation.
Extends the Stage 1 keyword logic with structured trigger definitions.

Stage 2 adds: configurable triggers, severity mapping, VIP detection.
Stage 3 will add: LLM-based sentiment classification via Claude API.
"""

# ---------------------------------------------------------------------------
# Escalation trigger definitions (extends Stage 1 ESCALATION_TRIGGERS)
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

# Complaint signals used for VIP detection
VIP_COMPLAINT_SIGNALS: list[str] = [
    "issue", "problem", "wrong", "error", "broken", "not working",
    "cancel", "disappointed", "unhappy", "frustrated",
]


# ---------------------------------------------------------------------------
# Core detection function
# ---------------------------------------------------------------------------

def detect_escalation(message: str, customer_context: dict) -> dict | None:
    """
    Determine whether this message requires human escalation.

    Checks in order:
      1. VIP/Enterprise customers with complaint signals → immediate escalation
      2. Keyword-based trigger matching against all ESCALATION_TRIGGERS

    Args:
        message: Raw customer message text.
        customer_context: Dict from get_customer_context MCP tool.
                          Must contain: is_vip (bool), account_tier (str).

    Returns:
        dict {"reason": str, "severity": str} if escalation required.
        None if no escalation needed.
    """
    message_lower = message.lower()
    is_vip = customer_context.get("is_vip", False)

    # Rule 1: VIP/Enterprise with complaint signal
    if is_vip or customer_context.get("account_tier", "").lower() == "enterprise":
        if any(signal in message_lower for signal in VIP_COMPLAINT_SIGNALS):
            return {"reason": "vip_complaint", "severity": "high"}

    # Rule 2: Keyword trigger matching
    for trigger in ESCALATION_TRIGGERS:
        if any(kw in message_lower for kw in trigger["keywords"]):
            return {"reason": trigger["reason"], "severity": trigger["severity"]}

    return None


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

INTENT_MAP: list[tuple[str, list[str]]] = [
    ("billing", ["invoice", "billing", "charge", "payment", "bill"]),
    ("account", ["login", "password", "locked", "access", "account"]),
    ("integration", ["slack", "google", "salesforce", "integration", "connect"]),
    ("plan", ["upgrade", "downgrade", "plan", "tier", "pricing"]),
    ("data", ["export", "download", "data", "backup"]),
    ("team", ["team", "invite", "user", "member", "add"]),
    ("cancellation", ["cancel", "cancellation", "unsubscribe"]),
    ("refund", ["refund", "money back", "reimburse"]),
    ("security", ["hacked", "breach", "unauthorized", "security"]),
    ("general", []),
]


def classify_intent(message: str) -> str:
    """
    Classify the primary intent of a customer message.

    Stage 2: Rule-based keyword matching.
    Stage 3: Claude API classification for nuanced intent detection.

    Args:
        message: Customer message text.

    Returns:
        Intent label string (e.g. "billing", "account", "general").
    """
    message_lower = message.lower()
    for intent, keywords in INTENT_MAP:
        if keywords and any(kw in message_lower for kw in keywords):
            return intent
    return "general"
