# Stage 3 System Architecture — Nexora Customer Success Digital FTE

**Stage:** 3 — Full AI System
**Project Owner:** Mehreen Asghar
**Hackathon:** Hackathon 5
**Version:** 3.0.0

---

## Overview

Stage 3 transforms the Stage 2 backend service into a complete AI-powered Customer Success system. It adds:

1. **AI Reasoning Layer** — LLM-powered response generation when the KB cannot answer
2. **Analytics Module** — per-interaction metrics and LLM cost tracking
3. **Frontend Dashboard** — Next.js dashboard for real-time monitoring and testing
4. **Extended API** — analytics endpoints for the dashboard

---

## Architecture Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────┐
│                           STAGE 3 SYSTEM                           │
│                                                                     │
│  ┌──────────┐  ┌─────────────┐  ┌──────────┐                       │
│  │  Gmail   │  │  WhatsApp   │  │ Web Form │   INBOUND CHANNELS    │
│  └────┬─────┘  └──────┬──────┘  └────┬─────┘                       │
│       │               │              │                              │
│       └───────────────┼──────────────┘                              │
│                       ▼                                             │
│            ┌──────────────────────┐                                 │
│            │   FastAPI Gateway    │   /support/gmail                │
│            │   (src/api/)         │   /support/whatsapp             │
│            │   CORS enabled       │   /support/webform              │
│            │   v3.0.0             │   /health                       │
│            └──────────┬───────────┘   /analytics/*                 │
│                       │                                             │
│                       ▼                                             │
│            ┌──────────────────────┐                                 │
│            │   Channel Handlers   │   normalize() → NormalizedMsg  │
│            │   (src/channels/)    │                                 │
│            └──────────┬───────────┘                                 │
│                       │                                             │
│                       ▼                                             │
│            ┌──────────────────────────────────────────┐            │
│            │          AI Agent Workflow                │            │
│            │          (src/agents/workflow.py)         │            │
│            │                                           │            │
│            │  1. Validate channel                      │            │
│            │  2. Identify/create customer              │            │
│            │  3. Get/create conversation               │            │
│            │  4. Customer context (MCP)                │            │
│            │  5. Classify intent                       │            │
│            │  6. Detect escalation                     │            │
│            │  7a. Search KB  ──► KB Hit ─────────────┐│            │
│            │  7b. LLM Reasoning (if KB miss)  ◄───────┘│            │
│            │  8. Create ticket                          │            │
│            │  9. Format channel response                │            │
│            │  10. Store + record analytics              │            │
│            └──────────┬───────────────────────────────┘            │
│                       │                                             │
│          ┌────────────┼─────────────────┐                           │
│          ▼            ▼                 ▼                           │
│  ┌──────────────┐ ┌────────┐ ┌────────────────────┐                │
│  │  KB Search   │ │  LLM   │ │  Escalation Engine  │               │
│  │  (MCP tool)  │ │ Client │ │  (rule-based)        │              │
│  └──────────────┘ └───┬────┘ └────────────────────┘                │
│                       │                                             │
│            ┌──────────┘                                             │
│            ▼                                                        │
│  ┌─────────────────────────────────────────────────┐               │
│  │                  MCP Tool Registry               │               │
│  │  search_kb · create_ticket · get_customer_context│               │
│  │  escalate_issue · send_channel_response          │               │
│  └─────────────────────┬───────────────────────────┘               │
│                        │                                            │
│            ┌───────────┼────────────┐                              │
│            ▼           ▼            ▼                              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                      │
│  │  Knowledge │ │   Ticket   │ │Conversation│   SERVICES           │
│  │  Service   │ │  Service   │ │  Service   │                      │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘                      │
│        └──────────────┼──────────────┘                              │
│                       ▼                                             │
│            ┌──────────────────────┐                                 │
│            │  SQLite / PostgreSQL  │   7 tables                     │
│            │  (src/db/)            │   SQLAlchemy ORM               │
│            └──────────────────────┘                                 │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   ANALYTICS MODULE (NEW)                      │   │
│  │   MetricsCollector  ·  UsageTracker  ·  /analytics/* API     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   NEXT.JS DASHBOARD (NEW)                     │   │
│  │   port 3000  ·  proxy: /api/backend/* → localhost:8000        │   │
│  │   Conversations · Tickets · Analytics · API Tester            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Reference

| Component | Path | Responsibility |
|-----------|------|----------------|
| FastAPI App | `src/api/main.py` | Application entry point, router registration, lifespan |
| Health API | `src/api/health.py` | GET /health — service status |
| Support API | `src/api/support_api.py` | POST /support/* — message ingestion |
| Analytics API | `src/api/analytics.py` | GET /analytics/* — metrics dashboard |
| Channel Handlers | `src/channels/` | Normalize inbound messages from each channel |
| Agent Workflow | `src/agents/workflow.py` | 10-step pipeline orchestrator |
| Escalation Engine | `src/agents/escalation_engine.py` | Rule-based escalation + intent classification |
| LLM Client | `src/llm/llm_client.py` | Multi-provider LLM interface |
| Prompt Templates | `src/llm/prompt_templates.py` | All prompts versioned here |
| Response Generator | `src/llm/response_generator.py` | 3-tier response strategy |
| MCP Tool Registry | `src/mcp/tool_registry.py` | Tool registration and dispatch |
| MCP Tools | `src/mcp/tools/` | 5 tools: KB search, ticket, context, escalate, send |
| DB Layer | `src/db/` | SQLAlchemy models, CRUD, session management |
| Services | `src/services/` | Business logic + data seeding |
| Metrics Collector | `src/analytics/agent_metrics.py` | Per-interaction performance metrics |
| Usage Tracker | `src/analytics/usage_tracking.py` | LLM token + cost tracking |
| Frontend | `frontend/` | Next.js 14 dashboard |

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| API Framework | FastAPI | 0.111.0 |
| ORM | SQLAlchemy | 2.0+ |
| Database | SQLite (dev) / PostgreSQL (prod) | — |
| AI Provider (primary) | Anthropic Claude | claude-sonnet-4-6 |
| AI Provider (alt 1) | OpenAI | gpt-4o-mini |
| AI Provider (alt 2) | Google Gemini | gemini-1.5-flash |
| Frontend Framework | Next.js | 14.2.3 |
| Frontend Language | TypeScript | 5+ |
| Frontend Styling | Tailwind CSS | 3.4+ |
| Testing | pytest | 8.2.0 |
| Python | Python | 3.11+ |

---

## Data Flow: Non-Escalated KB Miss (Full AI Path)

```
Customer → POST /support/gmail
  → GmailHandler.normalize()
  → process_message(customer_id, channel="email", content, db)
    → get_or_create_customer()
    → get_or_create_conversation()
    → call_tool("get_customer_context") → {account_tier, is_vip, ...}
    → classify_intent() → "general"
    → detect_escalation() → None (not escalated)
    → call_tool("search_kb") → {matched: False, results: []}
    → _try_llm_response() → ResponseGenerator.generate_response()
        → LLMClient.generate(system_prompt, user_prompt)
            → Anthropic API → LLMResponse{content, tokens}
        → GeneratedResponse{source="llm", content="...", tokens=247}
    → call_tool("create_ticket") → {ticket_ref: "TKT-0049", status: "auto-resolved"}
    → call_tool("send_channel_response") → formatted email text
    → crud.create_message() × 2 (customer + agent)
    → crud.create_metric()
    → _record_analytics(ai_used=True, tokens=247)
  → AgentResponse{success=True, ai_used=True, ai_provider="anthropic", ...}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./nexora_support.db` | Database connection string |
| `LLM_PROVIDER` | `anthropic` | LLM provider: anthropic / openai / gemini |
| `LLM_MODEL` | *(provider default)* | Model name override |
| `ANTHROPIC_API_KEY` | — | Required if `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | — | Required if `LLM_PROVIDER=openai` |
| `GEMINI_API_KEY` | — | Required if `LLM_PROVIDER=gemini` |
| `APP_ENV` | `development` | Environment label |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL for frontend |

---

## Deployment: Local Development

```bash
# Backend
pip install -r requirements.txt
uvicorn src.api.main:app --reload
# Swagger: http://localhost:8000/docs

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
# Dashboard: http://localhost:3000
```
