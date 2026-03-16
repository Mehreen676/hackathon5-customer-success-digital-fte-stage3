# Prompt History — Customer Success Digital FTE

**Project:** Nexora Customer Success AI Agent
**Owner:** Mehreen Asghar
**Hackathon:** Hackathon 5
**Stages Covered:** 1 (Prototype) → 2 (Backend Service) → 3 (Full AI System)

---

## Stage 1 Prompts

### Iteration 1: Define the Problem
**Starting point:**
Customer success teams at SaaS companies handle large volumes of repetitive, routine support tickets. The cost and delay of routing everything through human agents is high. Most tier-1 inquiries (password resets, billing questions, how-to questions) have standard answers.

**Decision:** Build a Digital FTE — an AI agent that handles tier-1 inquiries autonomously while detecting when human escalation is required.

**Why "Digital FTE" framing?**
It sets the right expectation: this is not just a chatbot. It is a full support agent that triages, looks up information, creates tickets, and routes work — exactly like a new hire would, but faster and without fatigue.

---

### Iteration 2: Define Stage 1 Scope

**Problem:** It's tempting to build the full system immediately (real Gmail, Twilio, database, LLM, Kubernetes). But that is months of work and a Stage 1 hackathon prototype needs to prove the *concept* quickly.

**Decision:** Stage 1 = simulated pipeline only. No real API integrations. Rule-based triage. In-memory data.

**What this validates:**
- Is the agent flow correct?
- Does triage logic catch the right cases?
- Does channel formatting work?
- Are the MCP tool interfaces well-designed?

**What it does NOT validate:** performance at scale, real LLM quality, production security.

**Why this was the right call:** Prototype-first avoids over-engineering before the design is stable.

---

### Iteration 3: Architecture Decision — One Agent, Multiple Channels

**Option A:** Build a separate agent per channel (EmailAgent, WhatsAppAgent, WebFormAgent).
**Option B:** Build one core agent that adapts output by channel.

**Decision:** Option B — single agent core.

**Reasoning:** Triage logic, KB search, and ticket creation are identical across channels. Only the response formatting differs. A single agent with a channel formatting layer is cleaner.

---

### Iteration 4: Triage Order Decision

**Early mistake:** In the first draft, the KB search ran before escalation check.

**Decision:** Escalation check always runs FIRST. KB search only runs if no escalation is triggered.

**Rule established:** `identify → triage → (if escalate: escalate path) → (else: KB → respond)`

---

### Iteration 5: MCP Tool Design

**Decision:** Structure all agent capabilities as MCP tools from the start, even in Stage 1.

**Tools defined:**
1. `search_kb`
2. `create_ticket`
3. `get_history`
4. `send_response`
5. `escalate_to_human`

---

### Iteration 6: KB Format Decision

**Decision:** Markdown files for Stage 1. Stage 2 will embed into DB.

**Reasoning:** Markdown is human-readable, easy to update, and the content can be scanned with simple keyword search.

---

### Iteration 7: Escalation Language

**Early draft:** "Your ticket has been escalated." (cold, clinical)

**Revised approach:** Empathy-first language — acknowledge feelings before mentioning handoff.

---

### Iteration 8: Test Strategy

**Decision:** One focused test file covering the four critical behaviors:
- Escalation detection, KB lookup, Channel formatting, Ticket creation

---

## Stage 2 Prompts

### Stage 2 — Prompt S2-001: Architecture Migration to FastAPI

**Date:** 2025-03-01
**Purpose:** Replace stateless Stage 1 prototype with a production-grade FastAPI service

**Prompt:**
> Design a Stage 2 backend service for the Customer Success Digital FTE. The Stage 1 prototype validated the concept but uses in-memory state. Stage 2 must add: FastAPI for REST API, SQLAlchemy with SQLite/PostgreSQL for persistence, real MCP tool implementations backed by the DB, and a proper 9-step agent workflow pipeline.

**Decision:** Introduce the `src/agents/workflow.py` as the single orchestrator. All MCP tools call through `tool_registry.py`. DB layer uses SQLAlchemy ORM with 7 tables.

---

### Stage 2 — Prompt S2-002: Database Schema Design

**Purpose:** Design 7 tables to support full CS agent persistence

**Prompt:**
> Design the SQLAlchemy ORM models for the Nexora CS agent. Required entities: customers (with VIP/tier tracking), customer_identifiers (map channel IDs to customers), conversations (threads), messages (individual turns), tickets (with escalation tracking), knowledge_base (KB articles with keyword search), agent_metrics (per-interaction performance).

**Decision:** UUID primary keys everywhere. Timezone-aware timestamps. `is_vip` flag on Customer for priority routing.

---

### Stage 2 — Prompt S2-003: Channel Handler Design

**Purpose:** Normalize all inbound channels to a single `NormalizedMessage` interface

**Prompt:**
> Design channel handlers for Gmail, WhatsApp (Twilio format), and Web Form. Each must normalize its input to a common NormalizedMessage schema so the workflow is channel-agnostic. Include customer_id derivation from email/phone when not provided.

**Decision:** `NormalizedMessage` dataclass with: customer_id, channel, content, customer_name, customer_email, metadata.

---

### Stage 2 — Prompt S2-004: Knowledge Base Seeding

**Purpose:** Pre-populate the DB with Nexora product knowledge articles

**Prompt:**
> Create 10 KB articles for Nexora's common support topics: password reset, billing/invoices, add team member, Slack integration, plan upgrade, refund policy, cancellation, data export, SSO setup, Google integration. Use the product-docs.md as source.

**Decision:** Idempotent seeding via `seed_knowledge_base()` — only inserts if topic doesn't exist.

---

### Stage 2 — Prompt S2-005: Escalation Engine

**Purpose:** Implement keyword-based escalation detection with severity levels

**Prompt:**
> Implement escalation detection that checks: (1) VIP customer + complaint signal, (2) keyword triggers for legal/security/refund/pricing/angry. Each trigger has a reason, severity (low/medium/high/critical), and keyword list.

**Decision:** `detect_escalation()` returns `{reason, severity}` dict or None. VIP detection runs first.

---

### Stage 2 — Prompt S2-006: MCP Tool Implementations

**Purpose:** Implement all 5 MCP tools backed by real DB operations

**Prompt:**
> Implement the 5 MCP tools: search_kb (keyword scoring + DB search with KNOWLEDGE_BASE_SEED fallback), create_ticket (DB-backed), get_customer_context (customer lookup + recent tickets), escalate_issue (DB update + channel-appropriate holding response), send_channel_response (formal/friendly/balanced formatting per channel).

---

### Stage 2 — Prompt S2-007: Test Suite Design

**Purpose:** 123 Stage 2 tests covering all new components

**Prompt:**
> Design test suites for Stage 2: test_api.py (26 tests, FastAPI TestClient), test_db.py (30 tests, in-memory SQLite), test_tools.py (33 tests, mocked DB), test_workflow.py (34 tests, end-to-end pipeline).

---

### Stage 2 — Prompt S2-008: Documentation

**Purpose:** Document Stage 2 architecture for judges

**Prompt:**
> Write stage2-architecture.md covering: system architecture diagram, component descriptions, database schema summary, API endpoint reference, workflow pipeline steps, MCP tool descriptions.

---

## Stage 3 Prompts

### Stage 3 — Prompt S3-001: Full Stage 3 System Design

**Date:** 2026-03-14
**Purpose:** Design and implement the complete Stage 3 system

**Prompt (verbatim):**
> Upgrade the existing Stage 3 repository for the project: Customer Success Digital FTE. Project Owner: Mehreen Asghar. Repository: hackathon5-customer-success-digital-fte-stage3. The current repository already contains the Stage 2 backend implementation. Do NOT delete any existing functionality. Extend the project to create a full Stage 3 system with: AI reasoning, frontend interface, enhanced architecture documentation, visual diagrams, demo assets, prompt history tracking, production-style structure.
>
> Stage 3 must transform the backend service into a complete AI Digital FTE system including: AI reasoning agent, LLM integration, frontend dashboard, improved workflow automation, analytics, visual documentation.

**Outcome:** Full Stage 3 implementation as documented in stage3-architecture.md.

---

### Stage 3 — Prompt S3-002: LLM Client Design

**Date:** 2026-03-14
**Purpose:** Design the multi-provider LLM abstraction layer

**Prompt:**
> Design src/llm/llm_client.py: a unified LLM client that supports Anthropic Claude, OpenAI GPT, and Google Gemini via a single interface. Provider and model selected via environment variables (LLM_PROVIDER, LLM_MODEL). Must: return LLMResponse dataclass, handle errors gracefully (return error field, not raise), support lazy API key loading from ANTHROPIC_API_KEY/OPENAI_API_KEY/GEMINI_API_KEY.

**Key decisions:**
- `generate()` is synchronous — simpler integration with FastAPI sync endpoints
- Default provider: `anthropic` (best quality for CS use case)
- Error response (not exception raise) enables graceful fallback in workflow

---

### Stage 3 — Prompt S3-003: Prompt Templates Design

**Date:** 2026-03-14
**Purpose:** Design versioned, channel-aware prompt templates

**Prompt:**
> Design src/llm/prompt_templates.py: all prompts for the CS AI agent as classmethods. Must include: system_prompt(channel) with full Nexora context and channel-specific tone guidelines, kb_response_prompt() for when KB has articles, no_kb_response_prompt() for KB misses, escalation_summary_prompt(), ticket_context_prompt().

**Key decisions:**
- All classmethods — no instantiation, easy to import and test
- Channel guidance embedded in system prompt (not separate API call)
- Customer context (VIP status, account tier) injected into user prompt

---

### Stage 3 — Prompt S3-004: Response Generator Design

**Date:** 2026-03-14
**Purpose:** Implement the 3-tier response strategy

**Prompt:**
> Design src/llm/response_generator.py: orchestrates KB → LLM → Fallback. The ResponseGenerator.generate_response() must: use KB content directly if matched (no LLM cost), call LLM if KB misses, fall back to polite holding message if LLM fails. Return GeneratedResponse with source field ("kb"/"llm"/"fallback").

**Key decisions:**
- Lazy LLM client init (only instantiated when needed)
- format_kb_response() handles channel-appropriate KB formatting
- Fallback messages are channel-aware (WhatsApp gets emoji)

---

### Stage 3 — Prompt S3-005: Workflow Extension

**Date:** 2026-03-14
**Purpose:** Extend workflow.py to add AI reasoning as Step 7b

**Prompt:**
> Extend src/agents/workflow.py to add Step 7b: after KB miss, call _try_llm_response(). The LLM response should be used if source is "llm". If source is "fallback", set ticket_status to "pending_review". If _try_llm_response returns None (import error or exception), use text fallback. Add analytics recording via _record_analytics(). Return dict must include: ai_used, ai_provider, ai_model, tokens_used, response_time_ms.

---

### Stage 3 — Prompt S3-006: Analytics Module Design

**Date:** 2026-03-14
**Purpose:** Design per-interaction metrics and LLM cost tracking

**Prompt:**
> Design src/analytics/agent_metrics.py: MetricsCollector class that records per-interaction data (channel, intent, response_source, response_time_ms, escalated, kb_used, ai_used, ticket_created, tokens_used). Thread-safe, singleton, persists to metrics_store.json. Provides get_summary() returning MetricsSummary with rates and aggregates.
>
> Also design src/analytics/usage_tracking.py: UsageTracker that tracks LLM token usage and computes cost from TOKEN_COSTS table. Support per-provider and daily aggregates.

---

### Stage 3 — Prompt S3-007: Analytics API Design

**Date:** 2026-03-14
**Purpose:** Expose analytics data to the frontend dashboard

**Prompt:**
> Design src/api/analytics.py: FastAPI router at /analytics/* with 3 endpoints: GET /analytics/summary (aggregate KPIs), GET /analytics/usage (LLM cost breakdown), GET /analytics/recent (recent interaction log). Must return demo data when no live data available so the dashboard always renders.

---

### Stage 3 — Prompt S3-008: Frontend Dashboard Design

**Date:** 2026-03-14
**Purpose:** Create the Next.js 14 monitoring and testing dashboard

**Prompt:**
> Create a Next.js 14 + TypeScript + Tailwind CSS dashboard for the Nexora Customer Success AI agent. Must include 6 sections: Dashboard Overview, Conversations (viewer + composer), Tickets (filterable list), Analytics (KPI cards + charts), API Tester (request builder), Settings. All sections must work without backend via mock data fallback. Backend communications via /api/backend/* Next.js proxy rewrite.

---

### Stage 3 — Prompt S3-009: Test Suite Extension

**Date:** 2026-03-14
**Purpose:** Add Stage 3 tests for LLM, frontend API compat, and reasoning pipeline

**Prompt:**
> Write three test files: test_llm.py (25+ tests for LLMClient, PromptTemplates, ResponseGenerator — all mocked, no real API keys), test_frontend_api.py (25+ tests verifying API responses have all fields expected by Next.js frontend — includes Stage 3 fields ai_used, ai_provider, response_time_ms), test_reasoning_pipeline.py (20+ tests for end-to-end workflow with LLM integration mocked).

---

### Stage 3 — Prompt S3-010: Documentation Suite

**Date:** 2026-03-14
**Purpose:** Complete Stage 3 documentation

**Prompt:**
> Write four Stage 3 spec files: stage3-architecture.md (full architecture with ASCII diagram), ai-reasoning-design.md (3-tier strategy, prompt engineering, cost table, security), frontend-design.md (component tree, API integration table, setup instructions), stage3-feature-matrix.md (full Stage 1/2/3 comparison table). Also update prompt-history.md with all Stage 3 prompts.

---

### Stage 3 — Prompt S3-011: README Rewrite

**Date:** 2026-03-14
**Purpose:** Update README to represent the complete Stage 3 system

**Prompt:**
> Rewrite README.md for Stage 3: add badges, demo section with asset references, Mermaid architecture diagram, AI reasoning explanation, frontend dashboard explanation, quick start commands, API reference table, environment variables table, test suite summary, stage comparison, full repository tree.

---

*End of prompt history — Stage 3 complete.*
