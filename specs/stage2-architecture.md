# Stage 2 System Architecture
### Customer Success Digital FTE — Hackathon 5

**Author:** Mehreen Asghar
**Stage:** 2 — Service Architecture

---

## Overview

Stage 2 converts the Stage 1 prototype into a production-ready backend service.
The stateless, in-memory prototype is replaced by a FastAPI service with database persistence,
a real MCP tool framework, multi-channel handlers, and a stateful agent workflow.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INBOUND CHANNELS                              │
│                                                                     │
│  ┌──────────────┐   ┌─────────────────┐   ┌──────────────────┐    │
│  │  Gmail API   │   │  WhatsApp Biz   │   │   Web Form UI    │    │
│  │  (simulated) │   │  (simulated)    │   │   (simulated)    │    │
│  └──────┬───────┘   └────────┬────────┘   └────────┬─────────┘    │
│         │                    │                      │               │
└─────────┼────────────────────┼──────────────────────┼───────────────┘
          │                    │                      │
          ▼                    ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND                               │
│                                                                     │
│   POST /support/gmail   POST /support/whatsapp   POST /support/webform
│   POST /support/message (unified)       GET /health                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    CHANNEL HANDLERS                          │   │
│  │  GmailHandler        WhatsAppHandler      WebFormHandler    │   │
│  │  normalize()         normalize()          normalize()       │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                             │ NormalizedMessage                     │
│  ┌──────────────────────────▼──────────────────────────────────┐   │
│  │                   AGENT WORKFLOW                             │   │
│  │                                                             │   │
│  │  1. Customer Identification (DB lookup / create)            │   │
│  │  2. Conversation Thread (get or create)                     │   │
│  │  3. Customer Context (MCP: get_customer_context)            │   │
│  │  4. Intent Classification                                   │   │
│  │  5. Escalation Detection (EscalationEngine)                 │   │
│  │     ├── YES → MCP: create_ticket + escalate_issue           │   │
│  │     └── NO  → MCP: search_kb                                │   │
│  │                ├── MATCH → KB response                      │   │
│  │                └── NO MATCH → fallback response             │   │
│  │  6. MCP: create_ticket                                      │   │
│  │  7. MCP: send_channel_response (channel formatting)         │   │
│  │  8. Store conversation history (DB)                         │   │
│  │  9. Record agent metrics (DB)                               │   │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                              │                                      │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
          ┌────────────────────┼───────────────────────┐
          ▼                    ▼                        ▼
┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│   MCP TOOLS     │  │    DATABASE       │  │   AGENT RESPONSE     │
│                 │  │  (SQLite / PgSQL) │  │                      │
│ search_kb       │  │                  │  │  AgentResponse JSON  │
│ create_ticket   │  │  customers        │  │  ├── ticket_ref      │
│ get_customer_   │  │  conversations    │  │  ├── escalated       │
│   context       │  │  messages         │  │  ├── kb_used         │
│ escalate_issue  │  │  tickets          │  │  ├── response text   │
│ send_channel_   │  │  knowledge_base   │  │  └── conversation_id │
│   response      │  │  agent_metrics    │  │                      │
└─────────────────┘  └──────────────────┘  └──────────────────────┘
```

---

## Key Architectural Differences: Stage 1 vs Stage 2

| Concern           | Stage 1 (Prototype)              | Stage 2 (Service)                          |
|-------------------|----------------------------------|--------------------------------------------|
| Storage           | In-memory dicts (lost on exit)   | SQLite / PostgreSQL via SQLAlchemy ORM     |
| API               | None (script only)               | FastAPI with OpenAPI docs                  |
| Channels          | Simulated via Python args        | Channel handlers with payload normalization|
| MCP Tools         | Plain functions in mcp_server.py | Registered via decorator in tool_registry  |
| Conversation      | Stateless                        | Persisted in conversations + messages tables|
| Ticket Storage    | TICKET_STORE dict                | tickets table with full lifecycle          |
| Metrics           | None                             | agent_metrics table                        |
| Testing           | Unit tests on functions          | API tests, DB tests, tool tests, workflow tests|
| Startup           | python script                    | uvicorn src.api.main:app                   |
| Configuration     | Hardcoded                        | Environment variables (.env)               |

---

## Module Responsibilities

### src/api/
- `main.py` — FastAPI app, lifespan (DB init, tool registration, seeding)
- `health.py` — GET /health with DB connectivity check
- `support_api.py` — All /support/* endpoints

### src/agents/
- `workflow.py` — The 9-step processing pipeline
- `customer_success_agent.py` — Public agent interface + Stage 1 fallback
- `escalation_engine.py` — Keyword-based escalation detection + intent classification

### src/channels/
- `gmail_handler.py` — Gmail payload → NormalizedMessage
- `whatsapp_handler.py` — WhatsApp payload → NormalizedMessage
- `webform_handler.py` — Web form payload → NormalizedMessage

### src/db/
- `database.py` — Engine, session factory, Base
- `models.py` — 7 ORM tables
- `crud.py` — All database read/write operations

### src/mcp/
- `tool_registry.py` — @register decorator + call_tool() dispatcher
- `tools/` — 5 individual tool implementations

### src/services/
- `knowledge_service.py` — KB seeding, KNOWLEDGE_BASE_SEED data
- `ticket_service.py` — Ticket lifecycle business logic
- `conversation_service.py` — Conversation history retrieval

### src/schemas/
- `message_schema.py` — Request models for all endpoints
- `ticket_schema.py` — Ticket response model
- `response_schema.py` — AgentResponse, HealthResponse

---

## Stage 3 Roadmap (not implemented)

- Real Gmail API (OAuth2 + push notifications)
- Real Twilio WhatsApp Business API
- Claude API for LLM-based intent classification and response generation
- Kafka for async message processing
- Kubernetes for production deployment
- Slack/PagerDuty notifications for escalated tickets
- CRM integration (Salesforce / HubSpot)
