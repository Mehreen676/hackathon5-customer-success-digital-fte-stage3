# Agent Skills — Customer Success Digital FTE

**Stage:** 1 Prototype
**Author:** Mehreen Asghar

This document lists all skills the Stage 1 agent prototype can perform, where they are implemented, and their current status.

---

## Skill 1: Identify Customer

**Description:** Look up the customer profile using their ID or contact details.

**What it does:**
- Searches mock customer store for a matching profile
- Returns account tier, name, contact info, and history summary
- If no match found, creates a guest profile

**Implementation:** `get_history()` in `mcp_server.py`
**Status:** Implemented (simulated)

---

## Skill 2: Check Escalation Triggers

**Description:** Scan the inbound message for patterns that require human escalation.

**What it does:**
- Checks message text against keyword lists for each escalation category
- Returns `escalate: True/False`, `reason`, and `severity`
- Agent stops auto-response flow if escalation is detected

**Triggers detected:**
- Refund request
- Pricing negotiation
- Legal complaint
- Angry/distressed customer
- VIP complaint
- Security issue

**Implementation:** `check_escalation()` in `customer_success_agent.py`
**Status:** Implemented

---

## Skill 3: Search Knowledge Base

**Description:** Search the local knowledge base for content relevant to the customer's question.

**What it does:**
- Tokenizes the query into keywords
- Scans KB content for matching paragraphs
- Returns top matches with source reference

**Implementation:** `search_kb()` in `mcp_server.py`
**Status:** Implemented (keyword match — semantic search in Stage 2)

---

## Skill 4: Format Response for Channel

**Description:** Transform a raw answer into a channel-appropriate message.

**What it does:**
- Applies the correct tone, length, and structure for the channel
- Email → formal salutation + detailed body + sign-off
- WhatsApp → brief, casual, plain text
- Web Form → structured, numbered if needed, includes ticket reference

**Implementation:** `send_response()` in `mcp_server.py`
**Status:** Implemented

---

## Skill 5: Create Support Ticket

**Description:** Log the customer interaction as a support ticket.

**What it does:**
- Assigns a unique ticket ID (e.g. TKT-00042)
- Records customer ID, channel, subject, message, and status
- Sets priority based on escalation severity
- Stores in-memory (demo only — no database in Stage 1)

**Implementation:** `create_ticket()` in `mcp_server.py`
**Status:** Implemented (in-memory only)

---

## Skill 6: Escalate to Human

**Description:** Flag a ticket for human agent review and generate an escalation holding response.

**What it does:**
- Marks ticket as `escalated`
- Records escalation reason and severity
- Generates channel-appropriate holding message for the customer
- In Stage 2: would notify human agent via Slack or CRM

**Implementation:** `escalate_to_human()` in `mcp_server.py`
**Status:** Implemented (notification is simulated)

---

## Skill 7: Retrieve Customer History

**Description:** Pull previous tickets and interactions for context.

**What it does:**
- Returns list of past tickets for the customer
- Summarizes recent interaction topics
- Flags if customer has a history of escalations (used to adjust priority)

**Implementation:** `get_history()` in `mcp_server.py`
**Status:** Implemented (mock data)

---

## Stage 2 Skills (Not in Stage 1)

| Skill | Description |
|---|---|
| Real LLM classification | Use Claude API to classify intent and generate responses |
| Semantic KB search | Replace keyword matching with vector embeddings |
| Conversation threading | Track multi-turn conversations per customer |
| Channel connectors | Receive real messages from Gmail and WhatsApp |
| CRM sync | Write ticket data to external CRM |
| Sentiment scoring | Score message sentiment on a continuous scale |
| Multilingual support | Detect and respond in customer's language |
