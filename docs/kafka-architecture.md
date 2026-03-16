# Kafka Architecture — Nexora Customer Success Digital FTE

**Component:** Event Streaming Layer
**Stage:** 3 (Production Architecture)

---

## Overview

Kafka decouples the HTTP ingestion layer (FastAPI) from the AI processing layer
(agent workers).  This enables:

- **Independent scaling** — ingest and process at different rates
- **Back-pressure handling** — workers consume at their own pace; Kafka buffers bursts
- **Replay** — reprocess messages from any offset without re-ingesting from channels
- **Audit trail** — every inbound message and response is durably stored
- **Multi-consumer** — analytics, CRM sync, and notification services can subscribe
  to the same topics without coupling

---

## Topic Map

```
Channel Input                   Kafka Topics                   Consumers
─────────────────────────────────────────────────────────────────────────
Gmail API webhook      ──►  gmail_incoming (6 partitions)  ──►  message-processor
Twilio WhatsApp hook   ──►  whatsapp_incoming (12 parts)   ──►  message-processor
Web form POST          ──►  webform_incoming (3 partitions) ──►  message-processor

                                                                     │
                                                              [AI Workflow]
                                                                     │
                                                                     ▼
                             agent_responses (6 parts)  ◄──  message-processor
                             escalations (3 parts)       ◄──  message-processor

Failed messages        ──►  dead_letter (1 partition)   ──►  retry-worker
                                                                     │
                                                              [back-off + retry]
                                                                     │
                                                                     ▼
                                               original topic (re-published)
```

---

## Topic Specifications

| Topic | Partitions | Retention | Purpose |
|-------|-----------|-----------|---------|
| `gmail_incoming` | 6 | 7 days | Inbound email payloads from Gmail API |
| `whatsapp_incoming` | 12 | 3 days | Inbound WhatsApp via Twilio (highest volume) |
| `webform_incoming` | 3 | 7 days | Inbound web form submissions |
| `agent_responses` | 6 | 3 days | Agent-generated responses ready for delivery |
| `escalations` | 3 | 30 days | Escalation events (audit trail required) |
| `dead_letter` | 1 | 30 days | Unprocessable messages after max retries |

---

## Message Envelope

Every Kafka message contains the original channel payload **plus** a `_meta` block:

```json
{
  "customer_id": "CUST-001",
  "channel": "email",
  "content": "I cannot find my invoice.",
  "from_email": "sarah@example.com",
  "from_name": "Sarah Chen",
  "_meta": {
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "produced_at": "2026-03-14T10:23:15.123+00:00",
    "producer_id": "nexora-producer-api-pod-1",
    "topic": "gmail_incoming",
    "retry_count": 0
  }
}
```

The `event_id` flows through all downstream topics for end-to-end tracing.

---

## Delivery Semantics

| Concern | Implementation |
|---------|---------------|
| At-least-once delivery | Consumer commits offset **after** successful handler return |
| Duplicate prevention | Workflow uses `get_or_create` DB operations (idempotent) |
| Message ordering | Partition key = `customer_id` → all messages for one customer go to same partition |
| Dead-letter routing | After `MAX_RETRIES` handler failures, message forwarded to `dead_letter` |
| Retry back-off | Exponential: 5s → 10s → 20s (configurable via `RETRY_BASE_BACKOFF_S`) |

---

## Scaling Strategy

- **API pods**: scale on HTTP request rate (HPA CPU metric)
- **Message processors**: scale on Kafka consumer lag (KEDA preferred over HPA)
- **Max replicas** bounded by partition count per topic
  - `gmail_incoming` (6 partitions) → max 6 processor replicas consuming that topic
  - `whatsapp_incoming` (12 partitions) → max 12 replicas

---

## Local Development (without Kafka)

The `NexoraProducer` and `NexoraConsumer` classes detect when `confluent-kafka`
is not installed and run in **DRY-RUN mode**:

- Producer: logs messages instead of sending
- Consumer: cannot consume (logs an error and returns)

The FastAPI API and AI workflow work fully without Kafka — messages are processed
synchronously in the HTTP request/response cycle.  Kafka becomes active when
`confluent-kafka` is installed and `KAFKA_BOOTSTRAP_SERVERS` is set.
