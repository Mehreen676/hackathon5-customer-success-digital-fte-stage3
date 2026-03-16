# Agent Workflow — Customer Success Digital FTE (Stage 2)

**Author:** Mehreen Asghar
**Stage:** 2 — Service Architecture

---

## Overview

The Stage 2 agent workflow is a 9-step stateful processing pipeline.
Every inbound message from any channel passes through the same pipeline.
All state (customers, conversations, messages, tickets, metrics) is persisted
to the database.

---

## Workflow Diagram

```
INBOUND MESSAGE (any channel)
          │
          ▼
┌─────────────────────┐
│ 1. CHANNEL DETECTION │  Determined by the endpoint called
│    + VALIDATION      │  email | whatsapp | web_form
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ 2. CUSTOMER IDENTIFICATION              │
│    get_customer_by_external_id(db, id)  │
│    → if not found: create_customer()    │
└──────────┬──────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│ 3. CONVERSATION THREAD                   │
│    get_active_conversation(db, cust, ch) │
│    → if none: create_conversation()      │
└──────────┬───────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ 4. CUSTOMER CONTEXT                     │
│    MCP: get_customer_context            │
│    → name, tier, is_vip, ticket history │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────┐
│ 5. INTENT           │
│    classify_intent  │
│    billing/account/ │
│    integration/plan │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│ 6. ESCALATION DETECTION                     │
│    detect_escalation(message, context)      │
│                                             │
│    VIP/Enterprise + complaint signal?  ─YES─┤
│    Keyword match in ESCALATION_TRIGGERS? ─NO┤
│                                             │
└────────────┬──────────────────┬─────────────┘
             │                  │
       escalated=YES       escalated=NO
             │                  │
             ▼                  ▼
┌────────────────────┐  ┌──────────────────────────┐
│ ESCALATION PATH    │  │ AUTO-RESPONSE PATH        │
│                    │  │                           │
│ MCP: create_ticket │  │ MCP: search_kb            │
│   status=escalated │  │   → scored keyword search │
│   priority=severity│  │   → fallback if no match  │
│                    │  │                           │
│ MCP: escalate_issue│  │ MCP: create_ticket        │
│   → DB update      │  │   status=auto-resolved or │
│   → team routing   │  │        pending_review     │
│   → SLA lookup     │  │                           │
│   → holding resp.  │  │ MCP: send_channel_response│
│                    │  │   email: formal + detailed │
│                    │  │   whatsapp: short + casual │
│                    │  │   web_form: structured     │
└────────────┬───────┘  └──────────────┬────────────┘
             │                          │
             └────────────┬─────────────┘
                          │
                          ▼
             ┌────────────────────────────┐
             │ 8. STORE CONVERSATION      │
             │    create_message(customer)│
             │    create_message(agent)   │
             └────────────┬───────────────┘
                          │
                          ▼
             ┌────────────────────────────┐
             │ 9. RECORD METRICS          │
             │    create_metric(...)      │
             │    processing_time_ms      │
             └────────────┬───────────────┘
                          │
                          ▼
             ┌────────────────────────────┐
             │ RETURN AgentResponse       │
             │   success, channel         │
             │   escalated, reason        │
             │   kb_used, kb_topic        │
             │   ticket_ref, response     │
             │   conversation_id          │
             └────────────────────────────┘
```

---

## Escalation Triggers

| Reason               | Severity | Assigned Team                  | SLA          |
|----------------------|----------|--------------------------------|--------------|
| security_issue       | critical | Security                       | 2 hours      |
| legal_complaint      | high     | Legal & Customer Success       | 2 hours      |
| vip_complaint        | high     | Account Management             | 2 hours      |
| angry_customer       | medium   | Senior Customer Success        | 1 business day|
| refund_request       | medium   | Billing                        | 1 business day|
| pricing_negotiation  | medium   | Sales & Account Management     | 1 business day|

---

## Auto-Response Topics (No Escalation)

| Topic            | KB Article          | Category    |
|------------------|---------------------|-------------|
| Password reset   | password_reset      | account     |
| Invoice / billing| billing_invoice     | billing     |
| Add team member  | add_team_member     | team        |
| Slack integration| slack_integration   | integration |
| Google Workspace | google_integration  | integration |
| Plan upgrade     | plan_upgrade        | billing     |
| Cancellation     | cancellation        | account     |
| Data export      | data_export         | data        |
| SSO setup        | sso_setup           | security    |
| Refund policy    | refund_policy       | billing     |

---

## Channel Response Styles

| Channel   | Style           | Word Limit | Salutation      | Sign-off                      |
|-----------|-----------------|------------|-----------------|-------------------------------|
| email     | Formal, detailed| 400 words  | Dear {first name}| Best regards, Nexora CS Team |
| whatsapp  | Conversational  | 80 words   | Hi {first name}! | Let me know if that helps! 👍|
| web_form  | Structured      | 200 words  | Thanks for reaching out | support@nexora.io     |

---

## MCP Tools Called Per Interaction

| Tool                  | Called When          | Purpose                        |
|-----------------------|----------------------|--------------------------------|
| get_customer_context  | Always               | Retrieve profile + history     |
| search_kb             | Not escalated        | Find relevant KB article       |
| create_ticket         | Always               | Create support ticket in DB    |
| escalate_issue        | Escalated only       | Update ticket + generate response |
| send_channel_response | Not escalated        | Format response for channel    |

---

## Stage 2 vs Stage 3 (planned)

| Capability       | Stage 2 (current)              | Stage 3 (planned)                        |
|------------------|--------------------------------|------------------------------------------|
| Intent detection | Keyword matching               | Claude API classification                |
| KB search        | Keyword scoring                | Vector similarity / Claude retrieval     |
| Response         | Template + KB content          | Claude API generated response            |
| Escalation notify| Logged only                   | Slack / PagerDuty real notification      |
| Channel delivery | Simulated (returned as JSON)   | Real Gmail API / Twilio delivery         |
