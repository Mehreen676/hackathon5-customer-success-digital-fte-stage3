# Customer Success Digital FTE — Stage 1 Specification

**Project:** Hackathon 5
**Author:** Mehreen Asghar
**Stage:** 1 — Prototype Foundation

---

## Overview

The Customer Success Digital FTE is an AI agent designed to autonomously handle first-line customer support. It operates across three channels (Gmail, WhatsApp, Web Form), triages incoming messages, answers routine questions using a knowledge base, creates tickets, and escalates to human agents when required.

This document covers the **Stage 1 prototype scope only**.

---

## Stage 1 Goals

1. Prove the agent flow end-to-end in a simulated environment
2. Validate triage and escalation logic with representative cases
3. Demonstrate channel-specific formatting
4. Define the MCP tool interface for future LLM integration
5. Establish the knowledge base structure and content

---

## Stage 1 Constraints

| Constraint | Reason |
|---|---|
| No real API integrations | Prototype only — APIs come in Stage 2 |
| No database | In-memory data is sufficient for Stage 1 |
| No real LLM calls | Logic is rule-based in Stage 1 to avoid API dependency |
| No authentication | Security layer is a Stage 2 concern |
| No async processing | Volume doesn't warrant it until Stage 2 |

---

## Supported Flows (Stage 1)

### Flow 1: Routine Inquiry — Auto-Respond

```
Customer message received
        ↓
Identify customer (mock lookup)
        ↓
Check escalation triggers → No escalation
        ↓
Search knowledge base → Match found
        ↓
Format response for channel
        ↓
Return formatted response + create ticket (status: auto-resolved)
```

### Flow 2: Escalation Required

```
Customer message received
        ↓
Identify customer (mock lookup)
        ↓
Check escalation triggers → Escalation trigger detected
        ↓
Do NOT auto-respond with KB content
        ↓
Generate empathy-first holding response
        ↓
Create ticket (status: escalated) + flag for human agent
        ↓
Return escalation response
```

### Flow 3: No KB Match

```
Customer message received
        ↓
Identify customer (mock lookup)
        ↓
Check escalation triggers → No escalation
        ↓
Search knowledge base → No match
        ↓
Return "connect you with a specialist" response
        ↓
Create ticket (status: pending_agent_review)
```

---

## Channel Specifications

### Gmail
- Formal salutation and sign-off required
- Full, detailed response — no truncation
- Reference ticket number in reply
- Max response length: ~400 words

### WhatsApp
- 3–5 lines maximum
- Casual, friendly opener
- Plain text only (no formatting)
- Max response length: ~100 words

### Web Form
- Acknowledge the submission
- Numbered steps if applicable
- Include ticket reference number
- Max response length: ~200 words

---

## Escalation Triggers (Stage 1)

| Trigger | Severity | Team |
|---|---|---|
| Refund request | MEDIUM | Billing |
| Pricing negotiation | MEDIUM | Sales |
| Legal complaint | HIGH | Legal + CS Manager |
| Angry/distressed customer | MEDIUM-HIGH | Senior CS Agent |
| VIP/Enterprise complaint | HIGH | Account Manager |
| Security issue | CRITICAL | Security + CS Manager |

---

## MCP Tool Interface (Stage 1 — Prototype)

All tools are Python functions in `src/agent/mcp_server.py`. In Stage 2, these will be exposed as real MCP protocol tools callable by Claude.

| Tool | Inputs | Outputs |
|---|---|---|
| `search_kb` | query (str) | list of matching KB snippets |
| `create_ticket` | customer_id, channel, subject, message, priority | ticket_id, status |
| `get_history` | customer_id | list of past tickets/messages |
| `send_response` | message, channel, customer_name | formatted response string |
| `escalate_to_human` | ticket_id, reason, severity | escalation confirmation |

---

## Demo Data (Stage 1)

Mock data includes:
- 5 customer profiles with different account tiers
- 8 historical support tickets across all channels
- Pre-loaded knowledge base content (4 topic areas)

All data is defined inline in Python — no database required.

---

## Success Criteria for Stage 1

- [ ] Agent processes a routine message and returns a correctly formatted channel response
- [ ] Agent detects all 6 escalation trigger types
- [ ] Agent produces visibly different responses for email vs WhatsApp vs web form
- [ ] Ticket is created for every processed message
- [ ] All 5 MCP tools execute without error
- [ ] Test suite passes with at least 10 assertions

---

## Out of Scope (Stage 1)

- Real Gmail, WhatsApp, or web form connectors
- Database persistence
- Real LLM / Claude API calls
- Authentication and authorization
- Kafka or any message queue
- Kubernetes or any deployment infrastructure
- External CRM integration
- Multi-turn conversation memory (each message is independent in Stage 1)
