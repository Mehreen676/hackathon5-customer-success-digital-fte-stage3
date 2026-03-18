---
title: Nexora Customer Success FTE
emoji: 🤖
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
---

# Nexora — Customer Success Digital FTE

### Stage 3: Full AI System with LLM Reasoning & Frontend Dashboard

[![Frontend Live](https://img.shields.io/badge/Frontend-Live%20on%20Vercel-000000?logo=vercel)](https://mehreen-nexora.vercel.app)
[![Backend Live](https://img.shields.io/badge/Backend-Live%20on%20HF%20Spaces-FFD21E?logo=huggingface&logoColor=000)](https://mehreenasghar5-nexora-customer-success-fte.hf.space)
[![API Docs](https://img.shields.io/badge/API%20Docs-Swagger%20UI-85EA2D?logo=swagger&logoColor=000)](https://mehreenasghar5-nexora-customer-success-fte.hf.space/docs)
![Stage](https://img.shields.io/badge/Stage-3-purple)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![Tests](https://img.shields.io/badge/Tests-384+-brightgreen)
![LLM](https://img.shields.io/badge/LLM-Claude%20%7C%20GPT--4o%20%7C%20Gemini-orange)
![Docker](https://img.shields.io/badge/Docker-24+-2496ED)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.28+-326CE5)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Hackathon 5 | Project Owner: Mehreen Asghar**

---

## Live Demo

| Service | URL |
|---------|-----|
| **Frontend (Vercel)** | [mehreen-nexora.vercel.app](https://mehreen-nexora.vercel.app) |
| **Backend API (Hugging Face Spaces)** | [mehreenasghar5-nexora-customer-success-fte.hf.space](https://mehreenasghar5-nexora-customer-success-fte.hf.space) |
| **API Docs (Swagger UI)** | [.../docs](https://mehreenasghar5-nexora-customer-success-fte.hf.space/docs) |
| **API Health Check** | [.../health](https://mehreenasghar5-nexora-customer-success-fte.hf.space/health) |

---

## Demo Video

[![Watch Demo Video](https://img.youtube.com/vi/2E3PR6svbDQ/0.jpg)](https://youtu.be/2E3PR6svbDQ)

A complete walkthrough of the Stage 3 Customer Success Digital FTE system — multi-channel AI support, LLM reasoning, and the live dashboard.

---

## Demo

> See live deployed app for real UI: [mehreen-nexora.vercel.app](https://mehreen-nexora.vercel.app)

**Architecture Diagram:**

![Architecture Diagram](assets/stage3-architecture.svg)

**Workflow Diagram:**

![Workflow Diagram](assets/stage3-workflow.svg)

---

## Stage 3 System Architecture

```mermaid
flowchart TD

A[Gmail] --> B(FastAPI Gateway)
C[WhatsApp] --> B
D[Web Form] --> B

B --> E[AI Agent Workflow]

E --> F[Knowledge Base]
E --> G[LLM Reasoning Layer]
E --> H[MCP Tools]

H --> I[Ticket Service]
I --> J[(SQL Database)]

E --> K[Response Formatter]

K --> L[Gmail Reply]
K --> M[WhatsApp Reply]
K --> N[Web Form Reply]

J --> O[Next.js Dashboard]
```

---

## AI Reasoning

### How LLM Is Used

The system applies a **3-tier response strategy** for every customer message:

| Tier | Source | When | LLM Cost |
|------|--------|------|----------|
| 1 | Knowledge Base | KB article matches customer query | $0 |
| 2 | LLM Generation | KB has no match — AI generates answer | ~$0.0003 |
| 3 | Fallback | LLM unavailable or fails | $0 |

**Multi-Provider Support:**

```bash
LLM_PROVIDER=anthropic   # → claude-sonnet-4-6 (default)
LLM_PROVIDER=openai      # → gpt-4o-mini
LLM_PROVIDER=gemini      # → gemini-1.5-flash
```

**Prompt Design:**
- System prompt encodes Nexora brand voice + channel-specific tone (email=formal, WhatsApp=brief/emoji)
- Customer context (account tier, VIP status, recent tickets) injected into the user prompt
- Escalation detection runs **before** the KB/LLM path — sensitive queries are never passed to the LLM

See [`specs/ai-reasoning-design.md`](specs/ai-reasoning-design.md) for full design documentation.

---

## Agents SDK Layer

The `agent/` package implements an **OpenAI Agents SDK style** architecture on top of the existing Stage 3 system. It adds typed tool inputs, a `FunctionTool` abstraction, and a structured `AgentRunner` pipeline — without replacing the existing FastAPI workflow.

### Architecture

```
backend/agent/
├── __init__.py               ← Public API exports
├── config.py                 ← AgentConfig, channel tones, escalation routing
├── models.py                 ← Typed Pydantic models for tool I/O + AgentResult
├── tools.py                  ← @function_tool decorated tools + FunctionTool class
└── customer_success_agent.py ← CustomerSuccessAgent + AgentRunner
```

### Quick Start

```python
from backend.agent import CustomerSuccessAgent, AgentRunner

# Build the default agent (uses env vars for LLM config)
agent = CustomerSuccessAgent.build()

# Run with an injected database session
runner = AgentRunner(db=session)
result = runner.run(agent, message="I can't find my invoice", context={
    "customer_id": "email:alice@example.com",
    "channel": "email",
    "customer_name": "Alice Johnson",
})

print(result.ticket_ref)       # TKT-XXXXXXXX
print(result.escalated)        # False
print(result.kb_used)          # True / False
print(result.ai_used)          # True / False
for tc in result.tool_calls:
    print(tc.tool_name, tc.success)  # get_customer_context True ...
```

### Tools

All 5 tools are registered via `@function_tool` with strict Pydantic input validation:

| Tool | Input Model | Delegates to |
|------|-------------|--------------|
| `search_knowledge_base` | `SearchKBInput` | `backend/mcp/tools/kb_search.py` |
| `create_ticket` | `CreateTicketInput` | `backend/mcp/tools/create_ticket.py` |
| `escalate_issue` | `EscalateIssueInput` | `backend/mcp/tools/escalate_issue.py` |
| `send_channel_response` | `SendChannelResponseInput` | `backend/mcp/tools/send_channel_response.py` |
| `get_customer_context` | `GetCustomerContextInput` | `backend/mcp/tools/get_customer_context.py` |

### How It Relates to `backend/agents/workflow.py`

| Aspect | `workflow.py` | `agent/` |
|--------|--------------|----------|
| Used by | FastAPI HTTP endpoints | Standalone / tests / external scripts |
| Tool dispatch | Raw `call_tool("name", ...)` | `FunctionTool.call(PydanticInput(...))` |
| Input validation | None | Pydantic (raises `ValidationError`) |
| Step trace | None | `ToolCall` list in `AgentResult` |
| Result type | Raw `dict` | Typed `AgentResult` |

Both paths call the same `backend/mcp/tools/*` and `backend/llm/*` code. No logic is duplicated.

### Swapping in the Real OpenAI Agents SDK

```python
# In agent/tools.py — change these two imports:
from agents import function_tool, FunctionTool   # real SDK

# In agent/customer_success_agent.py:
from agents import Agent as CustomerSuccessAgent
from agents import Runner as AgentRunner
```

All Pydantic input models and tool function bodies remain unchanged.

See [`specs/ai-reasoning-design.md`](specs/ai-reasoning-design.md) for full architecture documentation.

---

## Frontend Dashboard

The Next.js 14 dashboard (port 3000) communicates with the FastAPI backend (port 8000) via a proxy rewrite:

```
/api/backend/*  →  http://localhost:8000/*
```

**5 Panels:**

| Panel | Description |
|-------|-------------|
| 🏠 Dashboard | Architecture overview, quick nav, system stats |
| 💬 Conversations | View conversations, send test messages to the AI agent |
| 🎫 Tickets | Filterable ticket list with priority/status badges |
| 📊 Analytics | KPI cards, bar charts, response source distribution |
| 🔧 API Tester | Interactive request builder for all 4 channel endpoints |

The dashboard works without the backend running — all panels have mock data fallback.

See [`specs/frontend-design.md`](specs/frontend-design.md) for component documentation.

---

## Multi-Channel Integration

### Web Support Form

The public support page at `http://localhost:3000/support` provides a complete customer-facing interface:

| Component | File | Description |
|-----------|------|-------------|
| Support Page | `frontend/src/app/support/page.tsx` | Full-page layout with form + lookup |
| Support Form | `frontend/src/components/SupportForm.tsx` | Validated form, shows ticket ref on success |
| Ticket Lookup | `frontend/src/components/TicketStatusLookup.tsx` | Look up status by TKT-XXXXXXXX reference |

**Backend endpoints:**
- `POST /support/submit` — accepts the form submission, runs the agent pipeline
- `GET /support/ticket/{ref}` — returns ticket status, priority, latest agent response

### Gmail Webhook

**Endpoint:** `POST /webhooks/gmail`
**Caller:** Google Cloud Pub/Sub (push subscription)

```
Gmail → Pub/Sub topic → POST /webhooks/gmail (JSON)
                              ↓
                      parse_pubsub_notification()
                              ↓
                      GmailClient.fetch_message()
                              ↓
                      AI agent workflow
                              ↓
                      GmailClient.send_reply()  [live mode]
```

**Credentials:** Set `GMAIL_CREDENTIALS_PATH` + `GMAIL_USER_EMAIL`. Without them the handler runs in **MOCK mode** (no API calls, returns stub data).

### WhatsApp / Twilio Webhook

**Endpoint:** `POST /webhooks/whatsapp`
**Caller:** Twilio (form-encoded POST)

```
Customer → WhatsApp → Twilio → POST /webhooks/whatsapp (form-encoded)
                                       ↓
                               validate_twilio_signature()
                                       ↓
                               parse_twilio_webhook()
                                       ↓
                               AI agent workflow
                                       ↓
                               TwilioClient.send_whatsapp()  [live mode]
```

**Credentials:** Set `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` + `TWILIO_WHATSAPP_FROM`. Without them the handler runs in **MOCK mode**.

**Signature validation:** Enabled automatically when `TWILIO_AUTH_TOKEN` is set. Skipped in development.

See [`specs/integration-plan.md`](specs/integration-plan.md) for full setup instructions and credential requirements.

---

## Quick Start

### Backend

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure (optional — works without LLM for rule-based responses)
cp .env.example .env
# Edit .env: set LLM_PROVIDER and your API key

# 3. Start the API server
uvicorn backend.main:app --reload

# Swagger UI: http://localhost:8000/docs
# Health:     http://localhost:8000/health
# Analytics:  http://localhost:8000/analytics/summary
```

### Frontend

```bash
cd frontend
npm install
npm run dev

# Dashboard: http://localhost:3000
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# Stage 3 tests only
pytest tests/test_llm.py tests/test_frontend_api.py tests/test_reasoning_pipeline.py -v

# With coverage
pytest tests/ --cov=backend --cov-report=term-missing
```

---

## API Reference

| Method | Path | Channel | Request Body |
|--------|------|---------|--------------|
| GET | `/health` | — | — |
| POST | `/support/gmail` | Email | `GmailMessageRequest` |
| POST | `/support/whatsapp` | WhatsApp | `WhatsAppMessageRequest` |
| POST | `/support/webform` | Web Form | `WebFormRequest` |
| POST | `/support/message` | Generic | `GenericMessageRequest` |
| POST | `/support/submit` | Web Form | `WebFormRequest` (public support form) |
| GET | `/support/ticket/{ref}` | — | — (ticket status lookup) |
| POST | `/webhooks/gmail` | Email | `GmailPubSubPayload` (Google Pub/Sub) |
| POST | `/webhooks/whatsapp` | WhatsApp | Form-encoded (Twilio) |
| GET | `/analytics/summary` | — | — |
| GET | `/analytics/usage` | — | — |
| GET | `/analytics/recent` | — | `?limit=20` |

**Example Request:**

```bash
curl -X POST http://localhost:8000/support/gmail \
  -H "Content-Type: application/json" \
  -d '{
    "from_email": "sarah@example.com",
    "from_name": "Sarah Chen",
    "subject": "Cannot find my invoice",
    "body": "Hi, I need help finding my invoice from last month."
  }'
```

**Example Response (Stage 3):**

```json
{
  "success": true,
  "channel": "email",
  "customer": "Sarah Chen",
  "intent": "billing",
  "escalated": false,
  "kb_used": true,
  "kb_topic": "billing_invoice",
  "ai_used": false,
  "ai_provider": null,
  "tokens_used": 0,
  "response_time_ms": 187.3,
  "ticket": { "ticket_ref": "TKT-0049", "status": "auto-resolved", "priority": "low" },
  "response": "Dear Sarah Chen,\n\nThank you for reaching out...",
  "conversation_id": "conv-uuid-here"
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./nexora_support.db` | Database connection |
| `LLM_PROVIDER` | `anthropic` | `anthropic` / `openai` / `gemini` |
| `LLM_MODEL` | *(provider default)* | Model name override |
| `ANTHROPIC_API_KEY` | — | Required if `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | — | Required if `LLM_PROVIDER=openai` |
| `GEMINI_API_KEY` | — | Required if `LLM_PROVIDER=gemini` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL for frontend |
| `KAFKA_BOOTSTRAP_SERVERS` | — | e.g. `localhost:9092` — enables Kafka mode |
| `KAFKA_CONSUMER_GROUP` | `nexora-message-processors` | Consumer group ID |
| `MAX_RETRIES` | `3` | Dead-letter retry limit |
| `RETRY_BASE_BACKOFF_S` | `5` | Base seconds for exponential back-off |

Copy `.env.example` to `.env` to get started.

---

## Test Suite

| File | Tests | Coverage |
|------|-------|---------|
| `tests/test_agent.py` | 36 | Stage 1 prototype |
| `tests/test_api.py` | 26 | Stage 2 API endpoints |
| `tests/test_db.py` | 30 | Database CRUD |
| `tests/test_tools.py` | 33 | MCP tool implementations |
| `tests/test_workflow.py` | 34 | Stage 2 pipeline |
| `tests/test_llm.py` | 25+ | LLM module (Stage 3) |
| `tests/test_frontend_api.py` | 25+ | Frontend API compat (Stage 3) |
| `tests/test_reasoning_pipeline.py` | 20+ | AI reasoning pipeline (Stage 3) |
| `tests/test_webhooks.py` | 30+ | Gmail + WhatsApp webhooks (Stage 3) |
| `tests/test_support_form.py` | 30+ | Support form + ticket lookup (Stage 3) |
| `tests/test_agent_sdk.py` | 50+ | Agents SDK layer — tools, runner, channels (Stage 3) |
| **Total** | **339+** | |

---

## Stage Comparison

| | Stage 1 | Stage 2 | Stage 3 |
|-|---------|---------|---------|
| **Type** | Prototype | Backend Service | Full AI System |
| **State** | In-memory | SQLite/PostgreSQL | SQLite/PostgreSQL |
| **LLM** | ❌ | ❌ | ✅ Multi-provider |
| **Frontend** | ❌ | ❌ | ✅ Next.js 14 |
| **Analytics** | ❌ | Partial | ✅ Full module + API |
| **Agents SDK Layer** | ❌ | ❌ | ✅ `@function_tool`, `AgentRunner`, typed I/O |
| **Kafka Streaming** | ❌ | ❌ | ✅ 6 topics, DRY-RUN fallback |
| **Workers** | ❌ | ❌ | ✅ Message processor + retry |
| **Docker** | ❌ | ❌ | ✅ Multi-stage + compose |
| **Kubernetes** | ❌ | ❌ | ✅ HPA, Ingress, KEDA-ready |
| **Tests** | 36 | 159 | 229+ |
| **Docs** | Basic | Architecture | Full suite + diagrams |

---

## Production Architecture

### Kafka Event Streaming

The HTTP ingestion layer (FastAPI) is decoupled from the AI processing layer (workers) via Apache Kafka. This enables independent scaling, burst buffering, and full message replay.

```
Channel Input               Kafka Topics                    Consumers
──────────────────────────────────────────────────────────────────────
Gmail webhook     ──►  gmail_incoming     (6 parts)   ──►  message-processor
Twilio WhatsApp   ──►  whatsapp_incoming  (12 parts)  ──►  message-processor
Web form POST     ──►  webform_incoming   (3 parts)   ──►  message-processor

                                                              ▼
                       agent_responses   (6 parts)   ◄──  [AI Workflow]
                       escalations       (3 parts)   ◄──  [AI Workflow]

Failed messages   ──►  dead_letter       (1 part)    ──►  retry-worker
                                                              ▼
                                                   original topic (re-queued)
```

| Topic | Partitions | Retention | Purpose |
|-------|-----------|-----------|---------|
| `gmail_incoming` | 6 | 7 days | Inbound email payloads |
| `whatsapp_incoming` | 12 | 3 days | Inbound WhatsApp (highest volume) |
| `webform_incoming` | 3 | 7 days | Inbound web form submissions |
| `agent_responses` | 6 | 3 days | Agent-generated responses |
| `escalations` | 3 | 30 days | Escalation events (audit trail) |
| `dead_letter` | 1 | 30 days | Unprocessable messages |

**Delivery semantics:** at-least-once (offset committed after successful handler). Partition key = `customer_id` ensures message ordering per customer.

See [`docs/kafka-architecture.md`](docs/kafka-architecture.md) for full documentation.

---

### Worker Architecture

Two standalone Python processes consume Kafka topics independently of the HTTP API:

**Message Processor** (`workers/message_processor.py`)
- Consumes: `gmail_incoming`, `whatsapp_incoming`, `webform_incoming`
- Runs the full 10-step AI agent workflow per message
- Publishes results to `agent_responses` or `escalations`
- On handler failure: routes to `dead_letter` after `MAX_RETRIES=3`

**Retry Worker** (`workers/retry_worker.py`)
- Consumes: `dead_letter`
- Re-publishes to original topic with exponential back-off

| Attempt | Wait |
|---------|------|
| 1st retry | 5 s |
| 2nd retry | 10 s |
| 3rd retry | 20 s |
| Final | alert + discard |

```bash
# Run locally (requires confluent-kafka + KAFKA_BOOTSTRAP_SERVERS)
python -m workers.message_processor   # Terminal 1
python -m workers.retry_worker        # Terminal 2

# Without Kafka: workers log DRY-RUN and exit gracefully
```

See [`docs/worker-architecture.md`](docs/worker-architecture.md) for full documentation.

---

### Docker / Docker Compose

```bash
# Start the full stack (Kafka, Postgres, API, workers, frontend, Kafka UI)
docker compose up --build

# API:         http://localhost:8000
# Frontend:    http://localhost:3000
# Kafka UI:    http://localhost:8080
```

The `Dockerfile` uses a two-stage build (builder + slim runtime) with a non-root user (uid 1001) and a built-in `HEALTHCHECK`.

---

### Kubernetes Deployment

```bash
# 1. Create namespace
kubectl create namespace nexora

# 2. Apply secrets (fill in real values first)
kubectl create secret generic nexora-secrets \
  --from-literal=DATABASE_URL="postgresql://nexora:PASSWORD@host:5432/nexora_support" \
  --from-literal=ANTHROPIC_API_KEY="sk-ant-..." \
  --namespace=nexora

# 3. Apply all manifests
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# 4. Verify
kubectl get pods -n nexora
```

**Resource sizing:**

| Component | CPU (min→max) | Memory (min→max) | Replicas (min→max) |
|-----------|--------------|-----------------|-------------------|
| API | 250m → 1000m | 256Mi → 512Mi | 2 → 10 |
| Message Processor | 500m → 2000m | 384Mi → 768Mi | 2 → 12 |
| Retry Worker | 100m → 500m | 128Mi → 256Mi | 1 → 1 |

**HPA / KEDA:** The API autoscales on CPU (target 60%). The message processor autoscales on CPU (target 70%); a commented KEDA `ScaledObject` is provided in [`k8s/hpa.yaml`](k8s/hpa.yaml) for Kafka consumer-lag-based scaling (recommended for production).

See [`docs/kubernetes-deployment.md`](docs/kubernetes-deployment.md) for the full deployment guide.

---

## Repository Layout

> **Production-style layout** aligned with Hackathon 5 expectations.
> Each top-level folder has a single, clear responsibility.

| Folder / File | Purpose |
|---------------|---------|
| `backend/` | Deployable FastAPI service — all Python backend code lives here |
| `frontend/` | Next.js 14 dashboard + public support form + landing UI |
| `workers/` | Async Kafka consumer processes (message processor + retry worker) |
| `k8s/` | Kubernetes deployment manifests (Deployments, HPA, Ingress, Secrets) |
| `docs/` | Operations and deployment guides (runbook, monitoring, deployment) |
| `specs/` | Architecture and design documents (feature matrix, AI reasoning design) |
| `assets/` | SVG diagrams and visual assets |
| `context/` | Business context files fed to the AI agent (brand voice, product docs) |
| `monitoring/` | Prometheus scrape config + Alertmanager alert rules |
| `tests/` | Full test suite (384+ tests across 13 modules) |
| `agent/` | Top-level Agents SDK entry-point package |
| `app.py` | Hugging Face Spaces entry point — re-exports `backend.api.main:app` |

---

## Repository Structure

```
hackathon5-customer-success-digital-fte-stage3/
├── README.md
├── requirements.txt                   ← Python dependencies
├── .env.example                       ← Environment variable template
├── .gitignore
├── .gitattributes
├── .dockerignore
├── Dockerfile                         ← Single-stage build (HF Spaces compatible)
├── docker-compose.yml                 ← Full stack: Kafka, Postgres, API, workers, UI
├── startup.sh                         ← Waits for Postgres+Kafka, seeds DB, starts uvicorn
├── app.py                             ← HF Spaces entry point (re-exports backend.api.main:app)
│
├── backend/                           ← Deployable FastAPI backend
│   ├── __init__.py
│   ├── main.py                        ← Entry point: uvicorn backend.main:app
│   ├── api/
│   │   ├── main.py                    ← FastAPI app v3.0.0 (lifespan, CORS, routers)
│   │   ├── analytics.py               ← GET /analytics/summary|usage|recent
│   │   ├── support_api.py             ← POST /support/submit, GET /support/ticket/{ref}
│   │   ├── webhooks.py                ← POST /webhooks/gmail|whatsapp
│   │   └── health.py                  ← GET /health
│   ├── agent/                         ← Agents SDK style layer (CustomerSuccessAgent)
│   │   ├── __init__.py                ← Public exports
│   │   ├── config.py                  ← AgentConfig, channel tones, escalation routing
│   │   ├── models.py                  ← Typed Pydantic I/O models + AgentResult
│   │   ├── tools.py                   ← @function_tool + FunctionTool + 5 tools
│   │   └── customer_success_agent.py  ← CustomerSuccessAgent + AgentRunner (7-step)
│   ├── agent_v1/                      ← Stage 1 legacy agent (preserved, tested)
│   ├── agents/                        ← Stage 3 workflow engine
│   │   ├── workflow.py                ← 10-step AI pipeline
│   │   ├── escalation_engine.py
│   │   └── customer_success_agent.py
│   ├── analytics/                     ← Metrics + usage tracking
│   │   ├── agent_metrics.py           ← Thread-safe MetricsCollector singleton
│   │   └── usage_tracking.py          ← LLM token cost tracker
│   ├── channels/                      ← Email, WhatsApp, Web Form handlers
│   ├── database/                      ← SQLAlchemy ORM (7 tables)
│   │   ├── database.py                ← Engine, SessionLocal, get_db, init_db
│   │   ├── models.py                  ← ORM models
│   │   └── crud.py                    ← CRUD helpers
│   ├── integrations/                  ← External service clients (MOCK-safe)
│   │   ├── gmail_client.py            ← Gmail API, MOCK fallback
│   │   └── twilio_client.py           ← Twilio WhatsApp API, MOCK fallback
│   ├── llm/                           ← AI reasoning layer
│   │   ├── llm_client.py              ← Multi-provider client (Claude/GPT/Gemini)
│   │   ├── prompt_templates.py        ← Channel-aware versioned prompts
│   │   └── response_generator.py      ← 3-tier strategy: KB → LLM → fallback
│   ├── mcp/                           ← MCP tool registry + 5 tools
│   │   ├── tool_registry.py           ← @register decorator, call_tool(), init_tools()
│   │   └── tools/                     ← search_kb, create_ticket, escalate_issue, ...
│   ├── schemas/                       ← Pydantic request/response schemas
│   ├── services/                      ← Business logic + data seeding
│   ├── streaming/                     ← Kafka integration
│   │   ├── topics.py                  ← KafkaTopic frozen dataclasses
│   │   ├── kafka_producer.py          ← NexoraProducer (DRY-RUN fallback)
│   │   └── kafka_consumer.py          ← NexoraConsumer (manual offset commit)
│   └── webhooks/                      ← Inbound webhook payload parsers
│       ├── gmail_webhook.py           ← Google Pub/Sub notification decoder
│       └── whatsapp_webhook.py        ← Twilio form payload parser + sig validation
│
├── workers/                           ← Async Kafka consumer processes
│   ├── message_processor.py           ← Inbound topics → AI workflow → publish
│   └── retry_worker.py                ← dead_letter → exponential back-off → re-queue
│
├── frontend/                          ← Next.js 14 Dashboard + Public UI
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               ← Landing page (/)
│   │   │   ├── layout.tsx
│   │   │   ├── globals.css
│   │   │   ├── dashboard/page.tsx     ← Main dashboard (/dashboard)
│   │   │   ├── support/page.tsx       ← Public support form (/support)
│   │   │   ├── track-ticket/page.tsx  ← Ticket status lookup (/track-ticket)
│   │   │   └── landing/page.tsx       ← Legacy landing redirect
│   │   ├── components/
│   │   │   ├── Header.tsx             ← Top navigation bar
│   │   │   ├── Sidebar.tsx            ← Dashboard sidebar nav
│   │   │   ├── ConversationPanel.tsx
│   │   │   ├── TicketPanel.tsx
│   │   │   ├── AnalyticsPanel.tsx
│   │   │   ├── ApiTesterPanel.tsx
│   │   │   ├── SupportForm.tsx        ← Form with validation + ticket ref display
│   │   │   └── TicketStatusLookup.tsx ← TKT-XXXXXXXX lookup component
│   │   └── lib/api.ts                 ← Typed fetch client (relative imports)
│   ├── package.json
│   ├── vercel.json                    ← Vercel build config
│   └── next.config.mjs                ← Proxy /api/backend/* → :8000
│
├── k8s/                               ← Kubernetes manifests
│   ├── api-deployment.yaml            ← API Deployment (2 replicas, RollingUpdate)
│   ├── worker-deployment.yaml         ← message-processor + retry-worker Deployments
│   ├── service.yaml                   ← ClusterIP services (api, postgres, kafka)
│   ├── ingress.yaml                   ← Nginx ingress + TLS (api.nexora.io)
│   ├── hpa.yaml                       ← HPA (CPU/memory) + KEDA template
│   ├── configmap.yaml                 ← Non-secret config
│   └── secrets.example.yaml           ← Secret template (never commit real values)
│
├── docs/                              ← Operations and deployment guides
│   ├── deployment-guide.md            ← Local / Docker / Kubernetes / HF Spaces
│   ├── runbook.md                     ← 10 incident response playbooks
│   ├── monitoring-guide.md            ← Analytics API, Prometheus, Grafana, SLOs
│   ├── kafka-architecture.md          ← Kafka topics, partitioning, worker design
│   ├── worker-architecture.md         ← Retry worker deep-dive + back-off table
│   └── kubernetes-deployment.md       ← K8s manifest reference + HPA guide
│
├── specs/                             ← Design documentation
│   ├── stage3-architecture.md
│   ├── ai-reasoning-design.md
│   ├── frontend-design.md
│   ├── stage3-feature-matrix.md
│   ├── prompt-history.md
│   └── ...
│
├── assets/                            ← SVG diagrams + visual assets
│
├── context/                           ← Business context fed to the AI agent
│   ├── brand-voice.md
│   ├── company-profile.md
│   ├── escalation-rules.md
│   ├── product-docs.md
│   └── sample-tickets.json
│
├── monitoring/                        ← Prometheus + alerting
│   ├── prometheus.yml                 ← Scrape config (API, workers, Kafka, PG, Redis)
│   └── alerts.md                      ← 20 alert rules + Prometheus alert_rules.yml
│
└── tests/                             ← Full test suite (384+ tests)
    ├── test_agent.py                  ← Stage 1 prototype (36)
    ├── test_db.py                     ← Stage 2 DB layer (30)
    ├── test_tools.py                  ← MCP tools (33)
    ├── test_api.py                    ← REST API endpoints (26)
    ├── test_workflow.py               ← Stage 2 workflow (34)
    ├── test_llm.py                    ← LLM module (25+)
    ├── test_reasoning_pipeline.py     ← AI pipeline (20+)
    ├── test_frontend_api.py           ← Frontend API compat (25+)
    ├── test_webhooks.py               ← Gmail + WhatsApp webhooks (30+)
    ├── test_support_form.py           ← Support form + ticket lookup (30+)
    ├── test_agent_sdk.py              ← Agents SDK layer (50+)
    ├── test_multichannel_e2e.py       ← End-to-end all-channel E2E (45+)
    └── load_test.py                   ← Load simulation (standalone + Locust)
```

---

## Testing Summary

| Suite | File | Tests | Coverage |
|-------|------|-------|---------|
| Stage 1 Agent | `test_agent.py` | 36 | Core pipeline |
| Stage 2 DB | `test_db.py` | 30 | All 7 ORM models |
| Stage 2 MCP Tools | `test_tools.py` | 33 | All 5 MCP tools |
| Stage 2 API | `test_api.py` | 26 | All REST endpoints |
| Stage 2 Workflow | `test_workflow.py` | 34 | 10-step agent workflow |
| LLM Module | `test_llm.py` | 25+ | LLMClient, PromptTemplates, ResponseGenerator |
| AI Reasoning | `test_reasoning_pipeline.py` | 20+ | 3-tier strategy, KB→LLM→fallback |
| Frontend API Compat | `test_frontend_api.py` | 25+ | All analytics + support endpoints |
| Webhooks | `test_webhooks.py` | 30+ | Gmail Pub/Sub + Twilio WhatsApp |
| Support Form | `test_support_form.py` | 30+ | Web form submit, ticket lookup, cross-channel |
| Agents SDK | `test_agent_sdk.py` | 50+ | FunctionTool, AgentRunner, AgentResult, 7-step pipeline |
| **E2E Multi-Channel** | **`test_multichannel_e2e.py`** | **45+** | **Web form + Gmail + WhatsApp + cross-channel + lifecycle** |
| **Total** | | **~384+** | |

### Running the Full Test Suite

```bash
# All tests
pytest tests/ -v

# E2E tests only
pytest tests/test_multichannel_e2e.py -v

# Agents SDK tests
pytest tests/test_agent_sdk.py -v

# With coverage report
pytest tests/ --cov=backend --cov-report=term-missing
```

---

## Load Testing

The `tests/load_test.py` script simulates realistic multi-channel traffic with zero external dependencies.

### Standalone Mode (no extra packages)

```bash
# Default: 50 requests across all channels @ 10 RPS
python tests/load_test.py

# Custom: 200 requests @ 20 RPS with 4 workers
python tests/load_test.py --requests 200 --rps 20 --workers 4

# Channel-specific scenarios
python tests/load_test.py --scenario webform --requests 100 --rps 15
python tests/load_test.py --scenario gmail   --requests 50  --rps 10
python tests/load_test.py --scenario mixed   --requests 150 --rps 20
```

### Locust UI Mode (requires `pip install locust`)

```bash
locust -f tests/load_test.py --host http://localhost:8000
# Open http://localhost:8089 for the web UI
```

### Locust Headless

```bash
locust -f tests/load_test.py --host http://localhost:8000 \
  --headless --users 10 --spawn-rate 2 --run-time 60s
```

Three Locust user classes are defined: `WebFormUser` (40%), `GmailWebhookUser` (30%), `WhatsAppWebhookUser` (30%).

---

## Monitoring & Observability

### Analytics API (Always Available)

```bash
# KPI summary dashboard
curl http://localhost:8000/analytics/summary

# LLM token usage + cost by provider
curl http://localhost:8000/analytics/usage

# Recent interaction log
curl http://localhost:8000/analytics/recent
```

### Prometheus Metrics

```bash
# Start Prometheus with the included config
prometheus --config.file=monitoring/prometheus.yml

# Key queries
# Request rate:    rate(http_requests_total{job="nexora-api"}[5m])
# P95 latency:     histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
# Error rate:      rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
# Escalation rate: rate(nexora_escalations_total[1h]) / rate(nexora_tickets_created_total[1h])
```

See `docs/monitoring-guide.md` for the full metrics catalogue, alert thresholds, Grafana dashboard layout, and SLO definitions.

### Alerting

20 Prometheus alert rules defined in `monitoring/alerts.md` covering:
- Infrastructure: `ApiDown`, `ApiHighErrorRate`, `ApiHighLatency`, `PodCrashLooping`, `DatabaseConnectionFailed`, `KafkaConsumerLag`, `KafkaBrokerDown`
- Application: `LlmHighFallbackRate`, `LlmAllFallback`, `DailyLlmCostSpike`, `EscalationRateHigh`, `WebhookGmailFailures`, `WebhookWhatsappFailures`

---

## Operational Readiness

### Runbook Scenarios

The `docs/runbook.md` covers 10 incident response playbooks:

1. API Pod Restart / CrashLoopBackOff
2. Kafka Queue Backlog
3. Gmail Webhook Failures
4. WhatsApp Webhook Failures
5. Database Connection Issues
6. LLM Provider Outage
7. Retry Worker Stalled
8. High Response Latency
9. Frontend Offline
10. Analytics Data Missing

Each scenario includes: symptoms → diagnosis commands → remediation steps.

### Graceful Degradation

| Component Failure | System Behavior |
|------------------|-----------------|
| LLM provider down | Tier 3 fallback: holding message, `pending_review` ticket |
| Kafka down | Dry-run mode: events logged, not published |
| DB connection lost | 503 response with retry guidance |
| Gmail credentials missing | MOCK mode: logs what would be sent |
| Twilio credentials missing | MOCK mode: logs what would be sent |
| Analytics module error | Silently skipped; core pipeline unaffected |

---

## Deployment Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Backend** | ✅ Ready | `uvicorn backend.main:app` — FastAPI + SQLAlchemy + multi-provider LLM |
| **Frontend** | ✅ Ready | Next.js 14 dark dashboard — `npm run dev` or `npm run build` |
| **Docker** | ✅ Ready | `docker compose up --build` — 8-service full stack |
| **Kubernetes** | ✅ Ready | `k8s/` manifests with HPA, Ingress, KEDA-ready, Secrets |
| **Kafka Workers** | ✅ Ready | `workers/message_processor.py` + `workers/retry_worker.py` |
| **Monitoring** | ✅ Ready | Prometheus scrape config + 20 alert rules in `monitoring/` |
| **Tests** | ✅ Ready | 384+ tests across 13 modules — `pytest tests/ -v --cov=backend` |
| **Live Deployment** | ✅ Live | [Frontend](https://mehreen-nexora.vercel.app) · [Backend API](https://mehreenasghar5-nexora-customer-success-fte.hf.space) · [Swagger](https://mehreenasghar5-nexora-customer-success-fte.hf.space/docs) |

---

## Deployment

### Quick Start (Docker Compose)

```bash
# Copy and edit environment
cp .env.example .env

# Build and start all 8 services
docker-compose up --build

# Seed the database
docker-compose exec api python -m backend.services.knowledge_service
```

### Production (Kubernetes)

```bash
# Apply all manifests to nexora namespace
kubectl apply -f k8s/ -n nexora

# Verify rollout
kubectl rollout status deployment/nexora-api -n nexora
kubectl get hpa -n nexora
```

See `docs/deployment-guide.md` for full instructions covering:
- Local development setup
- Docker Compose full-stack
- Kubernetes manifests + HPA + Ingress
- Database migrations
- Rolling updates and rollbacks
- TLS/HTTPS setup
- Environment variable reference

---

*Hackathon 5 · Customer Success Digital FTE · Stage 3 · Mehreen Asghar*
