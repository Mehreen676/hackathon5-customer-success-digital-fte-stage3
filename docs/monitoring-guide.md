# Monitoring Guide — Nexora Customer Success Digital FTE (Stage 3)

**Project Owner:** Mehreen Asghar

---

## Overview

The Nexora platform exposes metrics and observability data through three layers:

| Layer | Mechanism | Endpoint / Location |
|-------|-----------|-------------------|
| Application metrics | Analytics REST API | `GET /analytics/*` |
| Infrastructure metrics | Prometheus scrape | `/metrics` (if prometheus-fastapi-instrumentator added) |
| Structured logs | Python `logging` → stdout | `kubectl logs` / log aggregation |
| Alerts | Prometheus Alertmanager rules | `monitoring/alerts.md` |

---

## 1. Analytics REST API

These endpoints are always available and require no external monitoring stack.

### 1.1 Summary Dashboard

```bash
GET /analytics/summary
```

Returns aggregate KPIs:

```json
{
  "total_conversations": 1240,
  "total_tickets": 1187,
  "escalation_rate": 0.08,
  "kb_hit_rate": 0.62,
  "ai_usage_rate": 0.31,
  "avg_response_time_ms": 187,
  "resolution_rate": 0.89
}
```

**Key metrics to watch:**

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|---------|
| `escalation_rate` | < 0.10 | 0.10–0.20 | > 0.20 |
| `kb_hit_rate` | > 0.50 | 0.30–0.50 | < 0.30 |
| `ai_usage_rate` | < 0.50 | 0.50–0.70 | > 0.70 |
| `avg_response_time_ms` | < 300 | 300–1000 | > 1000 |
| `resolution_rate` | > 0.80 | 0.60–0.80 | < 0.60 |

### 1.2 LLM Usage & Cost Breakdown

```bash
GET /analytics/usage
```

Returns per-provider token counts and estimated costs:

```json
{
  "total_llm_calls": 384,
  "total_input_tokens": 192000,
  "total_output_tokens": 57600,
  "estimated_cost_usd": 1.15,
  "by_provider": {
    "anthropic": {"calls": 200, "input_tokens": 100000, "output_tokens": 30000, "cost_usd": 0.75},
    "openai": {"calls": 184, "input_tokens": 92000, "output_tokens": 27600, "cost_usd": 0.40}
  }
}
```

**Alert threshold:** estimated daily cost > $5 USD → investigate spike.

### 1.3 Recent Interactions

```bash
GET /analytics/recent
GET /analytics/recent?limit=50
```

Returns a list of recent interaction records. Useful for debugging specific failures.

---

## 2. Prometheus Metrics

### 2.1 Scrape Configuration

See `monitoring/prometheus.yml` for the full scrape config.

```yaml
# Key scrape targets
scrape_configs:
  - job_name: nexora-api
    static_configs:
      - targets: ['nexora-api:8000']
    metrics_path: /metrics

  - job_name: nexora-workers
    static_configs:
      - targets: ['nexora-worker-retry:9090', 'nexora-worker-metrics:9091']
```

### 2.2 Exposed Metrics (when prometheus-fastapi-instrumentator is enabled)

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests by method, path, status |
| `http_request_duration_seconds` | Histogram | Request latency distribution |
| `http_requests_in_progress` | Gauge | Currently active requests |
| `nexora_tickets_created_total` | Counter | Tickets created by channel |
| `nexora_escalations_total` | Counter | Escalations by reason |
| `nexora_llm_calls_total` | Counter | LLM API calls by provider |
| `nexora_llm_tokens_total` | Counter | Tokens consumed by provider |
| `nexora_kb_hits_total` | Counter | KB search hits vs misses |
| `kafka_consumer_lag` | Gauge | Kafka consumer group lag |

### 2.3 Key Prometheus Queries

```promql
# Request rate (last 5 minutes)
rate(http_requests_total{job="nexora-api"}[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate (5xx responses)
rate(http_requests_total{status=~"5.."}[5m]) /
rate(http_requests_total[5m])

# Escalation rate
rate(nexora_escalations_total[1h]) /
rate(nexora_tickets_created_total[1h])

# LLM cost per hour (approximate)
increase(nexora_llm_tokens_total{type="output",provider="anthropic"}[1h]) * 0.000015

# Kafka consumer lag
kafka_consumer_lag{group="nexora-workers"}
```

---

## 3. Log Monitoring

### 3.1 Log Format

All application logs are JSON-structured via Python `logging`:

```json
{
  "timestamp": "2025-01-15T10:23:45.123Z",
  "level": "INFO",
  "logger": "src.agents.workflow",
  "message": "Ticket created",
  "ticket_ref": "TKT-A3F8B2",
  "channel": "email",
  "customer_id": "email:alice@example.com",
  "response_time_ms": 215,
  "ai_used": false,
  "escalated": false
}
```

### 3.2 Key Log Patterns to Monitor

| Pattern | Severity | Meaning |
|---------|----------|---------|
| `"LLM fallback"` | WARN | LLM unavailable; customer received holding message |
| `"Escalation detected"` | INFO | Customer routed to human team |
| `"parse_pubsub_notification failed"` | WARN | Malformed Gmail Pub/Sub message |
| `"Twilio signature invalid"` | WARN | Possible replay attack or misconfigured secret |
| `"DB connection error"` | ERROR | Database unavailable |
| `"Kafka producer error"` | ERROR | Event not published to Kafka |
| `"KafkaException"` | ERROR | Kafka broker unreachable |

### 3.3 Log Aggregation (Kubernetes)

```bash
# Stream API logs
kubectl logs -f -l app=nexora-api -n nexora

# Filter for errors only
kubectl logs -l app=nexora-api -n nexora | grep '"level":"ERROR"'

# Filter for escalations
kubectl logs -l app=nexora-api -n nexora | grep '"escalated":true'

# Count LLM fallbacks in last hour
kubectl logs -l app=nexora-api -n nexora | grep "LLM fallback" | wc -l
```

For production, pipe logs to a log aggregation stack (ELK / Loki + Grafana).

---

## 4. Grafana Dashboard

### 4.1 Recommended Panels

Create a Grafana dashboard with these panels:

**Row 1: Traffic**
- Requests/sec by endpoint (time series)
- P50 / P95 / P99 latency (time series)
- Error rate % (gauge)
- Active requests (gauge)

**Row 2: Business Metrics**
- Tickets created per channel per hour (bar chart)
- Escalation rate % (stat)
- KB hit rate % (stat)
- AI usage rate % (stat)

**Row 3: LLM**
- LLM calls per provider (pie chart)
- Token consumption over time (time series)
- Estimated cost per hour (stat)
- LLM error rate (stat)

**Row 4: Infrastructure**
- Kafka consumer lag (time series)
- DB connection pool utilization (gauge)
- Pod CPU / memory by service (time series)
- Pod restart count (stat)

### 4.2 Import Dashboard

A pre-built dashboard JSON template can be imported from `monitoring/grafana-dashboard.json` (Stage 4 scope).

---

## 5. Alerting Rules

See `monitoring/alerts.md` for the full Prometheus Alertmanager rule definitions.

**Summary of critical alerts:**

| Alert | Condition | Severity |
|-------|-----------|---------|
| `ApiHighErrorRate` | Error rate > 5% for 5 min | critical |
| `ApiHighLatency` | P95 > 2s for 5 min | warning |
| `KafkaConsumerLag` | Lag > 1000 for 10 min | warning |
| `LlmHighFallbackRate` | Fallback rate > 30% | warning |
| `DatabaseConnectionFailed` | DB unreachable for 1 min | critical |
| `PodCrashLooping` | Restarts > 5 in 15 min | critical |
| `DailyLlmCostSpike` | Estimated cost > $10/day | warning |

---

## 6. SLO Targets

| SLO | Target | Measurement |
|-----|--------|-------------|
| API availability | 99.9% | `1 - error_rate` over 30-day window |
| Response time P95 | < 500ms | `http_request_duration_seconds` histogram |
| Ticket creation success | > 99.5% | Tickets created / submissions attempted |
| Escalation routing | < 1 minute | Time from detection to team notification |
| LLM fallback rate | < 20% | Fallback responses / total KB-miss responses |

---

## 7. Incident Severity Levels

| Level | Criteria | Response Time | Examples |
|-------|----------|---------------|---------|
| P1 — Critical | Service down, all channels affected | 15 min | DB down, all API pods crashed |
| P2 — High | Partial outage, one channel affected | 30 min | Gmail webhook 100% failing |
| P3 — Medium | Degraded performance | 2 hours | LLM outage (fallback active), P95 > 1s |
| P4 — Low | Minor issue, no user impact | Next business day | Analytics data stale, worker backlog |
