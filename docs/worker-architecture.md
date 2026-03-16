# Worker Architecture — Nexora Customer Success Digital FTE

---

## Overview

Workers are standalone Python processes that consume Kafka topics and execute
the AI agent workflow independently of the HTTP API.  This allows:

- The API to return HTTP 202 Accepted immediately (async ingestion)
- Workers to scale horizontally based on Kafka partition count
- Resilient processing with at-least-once delivery and dead-letter handling

---

## Worker Types

### 1. Message Processor (`workers/message_processor.py`)

**Consumes:** `gmail_incoming`, `whatsapp_incoming`, `webform_incoming`
**Publishes:** `agent_responses`, `escalations`

```
[Kafka Consumer]
      │
      ▼
process_message(payload)
      │
      ├── Open DB session
      │
      ├── src.agents.workflow.process_message()
      │       ├── Customer identification
      │       ├── Escalation detection
      │       ├── KB search
      │       ├── LLM reasoning (if KB miss)
      │       ├── Ticket creation
      │       └── Metrics recording
      │
      ├── Publish to agent_responses OR escalations
      │
      └── Close DB session → commit Kafka offset
```

**Scaling:** Deploy N replicas where N ≤ max(partition counts).
Kafka distributes partitions evenly across consumer group members.

**Error handling:**
- Handler exception → offset NOT committed → message redelivered
- After `MAX_RETRIES` failures → message forwarded to `dead_letter`
- DB session always closed in `finally` block

---

### 2. Retry Worker (`workers/retry_worker.py`)

**Consumes:** `dead_letter`
**Publishes:** original topic (re-publish) or logs FINAL_FAILURE

```
[dead_letter Consumer]
      │
      ▼
handle_dead_letter(payload)
      │
      ├── Extract retry_count from _meta
      │
      ├── retry_count < MAX_RETRIES?
      │       │
      │       ├── YES: sleep(backoff) → re-publish to original topic
      │       │         retry_count incremented in _meta
      │       │
      │       └── NO:  log FINAL_FAILURE → _alert_on_call()
      │                commit offset (message discarded)
      │
      └── Commit offset
```

**Back-off formula:** `sleep = BASE_BACKOFF_S × (2 ^ retry_count)`

| Attempt | Wait |
|---------|------|
| 1st retry | 5s |
| 2nd retry | 10s |
| 3rd retry | 20s |
| Final failure | alert + discard |

---

## Running Workers Locally

```bash
# Terminal 1 — start message processor
python -m workers.message_processor

# Terminal 2 — start retry worker
python -m workers.retry_worker

# Without Kafka installed: workers log DRY-RUN messages and exit gracefully
```

---

## Running Workers via Docker

```bash
# Message processor
docker run --env-file .env nexora-cs-fte:3.0.0 \
  python -m workers.message_processor

# Retry worker
docker run --env-file .env nexora-cs-fte:3.0.0 \
  python -m workers.retry_worker
```

---

## Graceful Shutdown

Both workers register SIGINT and SIGTERM handlers that set `_running = False`.
The consumer poll loop exits cleanly after the current message is processed.
`terminationGracePeriodSeconds: 60` in the k8s Deployment allows in-flight
LLM calls to complete before the pod is killed.
