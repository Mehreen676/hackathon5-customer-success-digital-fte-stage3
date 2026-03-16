"""
Knowledge Service — Customer Success Digital FTE (Stage 2)

Manages the knowledge base: seeding initial content from Stage 1,
and providing the canonical KB data for the fallback search.
"""

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical knowledge base seed data
# Mirrors Stage 1's KNOWLEDGE_BASE — single source of truth for seeding.
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE_SEED: list[dict] = [
    {
        "topic": "password_reset",
        "category": "account",
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
        "category": "billing",
        "keywords": ["invoice", "billing", "receipt", "payment", "charge", "bill"],
        "content": (
            "Invoices are available in Settings > Billing > Invoices. "
            "You can download PDF invoices for all past payments. "
            "Your billing date is the same day of the month you originally subscribed."
        ),
    },
    {
        "topic": "add_team_member",
        "category": "team",
        "keywords": ["add", "invite", "team", "member", "user", "colleague", "new user"],
        "content": (
            "To add a team member: go to Settings > Team Members > Invite User. "
            "Enter their email and choose their role (Viewer, Editor, or Admin). "
            "They will receive an email invitation to join your workspace."
        ),
    },
    {
        "topic": "slack_integration",
        "category": "integration",
        "keywords": ["slack", "integration", "connect", "integrate", "notification"],
        "content": (
            "To connect Slack: go to Settings > Integrations > Slack > Connect. "
            "You will be prompted to authorize the Nexora Slack app in your workspace. "
            "Once connected, you can receive task notifications directly in Slack."
        ),
    },
    {
        "topic": "plan_upgrade",
        "category": "billing",
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
        "category": "billing",
        "keywords": ["refund", "money back", "return", "cancel", "reimburse"],
        "content": (
            "Nexora offers refunds within 14 days of the initial purchase or renewal for annual plans. "
            "Monthly plans are non-refundable after the billing date. "
            "All refund requests are reviewed by the billing team within 1 business day."
        ),
    },
    {
        "topic": "cancellation",
        "category": "account",
        "keywords": ["cancel", "cancellation", "unsubscribe", "stop", "end subscription"],
        "content": (
            "To cancel your subscription: go to Settings > Billing > Plan > Cancel Subscription. "
            "Your account remains active until the end of the current billing period. "
            "You can reactivate at any time."
        ),
    },
    {
        "topic": "data_export",
        "category": "data",
        "keywords": ["export", "download", "data", "backup", "extract"],
        "content": (
            "To export your data: go to Settings > Data > Export. "
            "You can export all projects, tasks, and documents as a ZIP file. "
            "Export requests are processed within 24 hours."
        ),
    },
    {
        "topic": "sso_setup",
        "category": "security",
        "keywords": ["sso", "single sign-on", "saml", "okta", "identity", "login"],
        "content": (
            "SSO is available on Business and Enterprise plans only. "
            "Setup: go to Settings > Security > SSO and follow the SAML 2.0 guide. "
            "For Enterprise SSO setup, contact your dedicated account manager."
        ),
    },
    {
        "topic": "google_integration",
        "category": "integration",
        "keywords": ["google", "google workspace", "drive", "docs", "calendar"],
        "content": (
            "To connect Google Workspace: go to Settings > Integrations > Google > Connect. "
            "You can link Google Drive, Google Docs, and Google Calendar to Nexora projects. "
            "Requires Google Workspace admin approval for your organisation."
        ),
    },
]

# ---------------------------------------------------------------------------
# Stage 1 customer seed data
# ---------------------------------------------------------------------------

CUSTOMER_SEED: list[dict] = [
    {
        "external_id": "CUST-001",
        "name": "Sarah Mitchell",
        "email": "sarah.mitchell@brightflow.com",
        "account_tier": "growth",
        "is_vip": False,
    },
    {
        "external_id": "CUST-002",
        "name": "James Okafor",
        "email": "james.okafor@deltaops.io",
        "account_tier": "starter",
        "is_vip": False,
    },
    {
        "external_id": "CUST-003",
        "name": "Priya Sharma",
        "email": "priya@techbridge.net",
        "account_tier": "business",
        "is_vip": False,
    },
    {
        "external_id": "CUST-004",
        "name": "Daniel Cruz",
        "email": "d.cruz@constructly.com",
        "account_tier": "growth",
        "is_vip": False,
    },
    {
        "external_id": "CUST-005",
        "name": "Amara Diallo",
        "email": "amara.diallo@lunarcorp.io",
        "account_tier": "enterprise",
        "is_vip": True,
    },
]


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------

def seed_knowledge_base(db: Session) -> int:
    """
    Seed the knowledge base table with canonical content.
    Only inserts entries that don't already exist (idempotent).

    Returns:
        Number of entries inserted.
    """
    from backend.database import crud

    inserted = 0
    for entry in KNOWLEDGE_BASE_SEED:
        existing = crud.get_kb_entry_by_topic(db, entry["topic"])
        if not existing:
            crud.create_kb_entry(
                db=db,
                topic=entry["topic"],
                keywords=", ".join(entry["keywords"]),
                content=entry["content"],
                category=entry["category"],
            )
            inserted += 1

    if inserted:
        logger.info("Seeded %d knowledge base entries", inserted)
    else:
        logger.debug("Knowledge base already seeded — no new entries added")

    return inserted


def seed_customers(db: Session) -> int:
    """
    Seed the customers table with Stage 1 sample customer data.
    Only inserts customers that don't already exist (idempotent).

    Returns:
        Number of customers inserted.
    """
    from backend.database import crud

    inserted = 0
    for c in CUSTOMER_SEED:
        existing = crud.get_customer_by_external_id(db, c["external_id"])
        if not existing:
            crud.create_customer(
                db=db,
                external_id=c["external_id"],
                name=c["name"],
                email=c["email"],
                account_tier=c["account_tier"],
                is_vip=c["is_vip"],
            )
            inserted += 1

    if inserted:
        logger.info("Seeded %d customer records", inserted)

    return inserted


def seed_all(db: Session) -> dict:
    """Run all seed operations. Safe to call on every startup."""
    kb_count = seed_knowledge_base(db)
    cust_count = seed_customers(db)
    return {"kb_entries_seeded": kb_count, "customers_seeded": cust_count}
