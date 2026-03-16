# Alerting Rules — Nexora Customer Success Digital FTE (Stage 3)

This file documents all Prometheus alerting rules.
The equivalent `alert_rules.yml` (Prometheus format) is included at the end.

---

## Alert Index

| Alert Name | Severity | Condition | Action |
|-----------|----------|-----------|--------|
| `ApiDown` | critical | API pod unreachable for 1 min | Page on-call; check pod logs |
| `ApiHighErrorRate` | critical | 5xx error rate > 5% for 5 min | Check logs; rollback if recent deploy |
| `ApiHighLatency` | warning | P95 latency > 2s for 5 min | Scale pods; check DB/LLM |
| `ApiVeryHighLatency` | critical | P95 latency > 5s for 5 min | Immediate investigation |
| `PodCrashLooping` | critical | Pod restarts > 5 in 15 min | Check pod logs; rollback |
| `DatabaseConnectionFailed` | critical | DB unreachable for 2 min | Restart DB pod; check PVC |
| `DatabaseHighConnections` | warning | Connections > 80% of pool | Scale down API; increase pool |
| `KafkaConsumerLag` | warning | Consumer lag > 1000 for 10 min | Scale up workers |
| `KafkaConsumerLagCritical` | critical | Consumer lag > 10000 for 15 min | Emergency worker scale-up |
| `KafkaBrokerDown` | critical | Kafka broker unreachable for 2 min | API runs in dry-run mode |
| `LlmHighFallbackRate` | warning | LLM fallback rate > 30% for 10 min | Check LLM API keys/provider status |
| `LlmAllFallback` | critical | LLM fallback rate = 100% for 5 min | LLM provider is down |
| `DailyLlmCostSpike` | warning | Est. daily LLM cost > $10 | Check for abnormal traffic |
| `EscalationRateHigh` | warning | Escalation rate > 20% for 30 min | Review escalation triggers |
| `KbHitRateLow` | warning | KB hit rate < 20% for 1 hour | Review KB articles |
| `WebhookGmailFailures` | warning | Gmail webhook error rate > 10% | Check Pub/Sub; Gmail credentials |
| `WebhookWhatsappFailures` | warning | WhatsApp webhook error rate > 10% | Check Twilio config |
| `FrontendDown` | warning | Frontend pod unreachable for 2 min | Check Next.js pod; ingress |
| `MemoryPressure` | warning | Pod memory > 80% of limit | Check for leaks; increase limits |
| `DiskSpaceRunningOut` | warning | PVC usage > 80% | Expand PVC or archive data |

---

## Alert Definitions

### Infrastructure Alerts

---

#### `ApiDown`
- **Severity:** critical
- **Condition:** The nexora-api scrape target has been down for more than 1 minute.
- **PromQL:**
  ```promql
  up{job="nexora-api"} == 0
  ```
- **Duration:** 1m
- **On-call action:**
  1. `kubectl get pods -n nexora -l app=nexora-api`
  2. `kubectl describe pod <pod> -n nexora` — look for OOMKilled / ImagePullError
  3. `kubectl rollout undo deployment/nexora-api -n nexora` if recent deploy

---

#### `ApiHighErrorRate`
- **Severity:** critical
- **Condition:** HTTP 5xx error rate exceeds 5% sustained for 5 minutes.
- **PromQL:**
  ```promql
  (
    rate(http_requests_total{job="nexora-api",status=~"5.."}[5m])
    /
    rate(http_requests_total{job="nexora-api"}[5m])
  ) > 0.05
  ```
- **Duration:** 5m
- **On-call action:**
  1. Check recent deployments: `kubectl rollout history deployment/nexora-api -n nexora`
  2. Check API logs for stack traces
  3. If DB related, check `DatabaseConnectionFailed` alert

---

#### `ApiHighLatency`
- **Severity:** warning
- **Condition:** P95 response time exceeds 2 seconds for 5 minutes.
- **PromQL:**
  ```promql
  histogram_quantile(0.95,
    rate(http_request_duration_seconds_bucket{job="nexora-api"}[5m])
  ) > 2.0
  ```
- **Duration:** 5m
- **On-call action:**
  1. Check `GET /analytics/summary` for slow LLM usage
  2. Check Kafka lag (LLM may be queuing)
  3. Scale API: `kubectl scale deployment nexora-api --replicas=5 -n nexora`

---

#### `PodCrashLooping`
- **Severity:** critical
- **Condition:** Any nexora pod has restarted more than 5 times in 15 minutes.
- **PromQL:**
  ```promql
  increase(kube_pod_container_status_restarts_total{namespace="nexora"}[15m]) > 5
  ```
- **Duration:** 0m (immediate)
- **On-call action:**
  1. `kubectl logs <pod> --previous -n nexora`
  2. Check for OOMKilled or missing secrets
  3. Rollback if related to recent deploy

---

#### `DatabaseConnectionFailed`
- **Severity:** critical
- **Condition:** PostgreSQL exporter reports no active connections for 2 minutes.
- **PromQL:**
  ```promql
  pg_up{job="postgres"} == 0
  ```
- **Duration:** 2m
- **On-call action:**
  1. `kubectl get pods -n nexora -l app=postgres`
  2. `kubectl logs -l app=postgres -n nexora --tail=50`
  3. Check PVC: `kubectl get pvc -n nexora`

---

#### `KafkaConsumerLag`
- **Severity:** warning
- **Condition:** Consumer group lag exceeds 1,000 messages for 10 minutes.
- **PromQL:**
  ```promql
  kafka_consumer_group_lag{group="nexora-workers"} > 1000
  ```
- **Duration:** 10m
- **On-call action:**
  1. Scale up workers: `kubectl scale deployment nexora-worker-retry --replicas=3 -n nexora`
  2. Check worker logs for errors

---

#### `KafkaBrokerDown`
- **Severity:** critical
- **Condition:** Kafka broker is unreachable for 2 minutes.
- **PromQL:**
  ```promql
  kafka_brokers{job="kafka"} == 0
  ```
- **Duration:** 2m
- **Notes:** API automatically switches to dry-run mode (events logged, not published).

---

### Application Alerts

---

#### `LlmHighFallbackRate`
- **Severity:** warning
- **Condition:** LLM fallback (rule-based holding message) rate exceeds 30% of LLM-attempted responses for 10 minutes.
- **PromQL:**
  ```promql
  (
    rate(nexora_llm_fallbacks_total[10m])
    /
    (rate(nexora_llm_calls_total[10m]) + rate(nexora_llm_fallbacks_total[10m]))
  ) > 0.30
  ```
- **Duration:** 10m
- **On-call action:**
  1. Check provider status pages
  2. Switch provider: `kubectl set env deployment/nexora-api LLM_PROVIDER=openai -n nexora`
  3. Check API key validity

---

#### `DailyLlmCostSpike`
- **Severity:** warning
- **Condition:** Estimated daily LLM cost (based on 24h token consumption rate) exceeds $10 USD.
- **PromQL:**
  ```promql
  (
    increase(nexora_llm_tokens_total{type="output",provider="anthropic"}[24h]) * 0.000015
    +
    increase(nexora_llm_tokens_total{type="input",provider="anthropic"}[24h]) * 0.000003
  ) > 10
  ```
- **Duration:** 0m
- **On-call action:**
  1. Check `GET /analytics/usage` for breakdown
  2. Investigate unusual traffic spikes
  3. Consider rate limiting if abuse detected

---

#### `EscalationRateHigh`
- **Severity:** warning
- **Condition:** Escalation rate exceeds 20% of all tickets for 30 minutes.
- **PromQL:**
  ```promql
  (
    rate(nexora_escalations_total[30m])
    /
    rate(nexora_tickets_created_total[30m])
  ) > 0.20
  ```
- **Duration:** 30m
- **Notes:** May indicate a product issue, PR crisis, or attack. Alert the relevant team.

---

#### `WebhookGmailFailures`
- **Severity:** warning
- **Condition:** Gmail webhook endpoint returning non-200 responses at > 10% rate.
- **PromQL:**
  ```promql
  (
    rate(http_requests_total{path="/webhooks/gmail",status!="200"}[5m])
    /
    rate(http_requests_total{path="/webhooks/gmail"}[5m])
  ) > 0.10
  ```
- **Duration:** 5m
- **Notes:** Gmail Pub/Sub will retry on non-200. This alert fires before the queue backs up.

---

## Prometheus alert_rules.yml

Save this file as `monitoring/alert_rules.yml` and reference it in `prometheus.yml` under `rule_files`.

```yaml
groups:
  - name: nexora.infrastructure
    interval: 30s
    rules:
      - alert: ApiDown
        expr: up{job="nexora-api"} == 0
        for: 1m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Nexora API is down"
          description: "nexora-api scrape target {{ $labels.instance }} has been unreachable for more than 1 minute."
          runbook: "https://github.com/your-org/nexora/blob/main/docs/runbook.md#1-api-pod-restart--crashloopbackoff"

      - alert: ApiHighErrorRate
        expr: |
          (
            rate(http_requests_total{job="nexora-api",status=~"5.."}[5m])
            /
            rate(http_requests_total{job="nexora-api"}[5m])
          ) > 0.05
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "High HTTP 5xx error rate on Nexora API"
          description: "5xx error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

      - alert: ApiHighLatency
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket{job="nexora-api"}[5m])
          ) > 2.0
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High P95 latency on Nexora API"
          description: "P95 latency is {{ $value | humanizeDuration }} (threshold: 2s)"

      - alert: PodCrashLooping
        expr: increase(kube_pod_container_status_restarts_total{namespace="nexora"}[15m]) > 5
        for: 0m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Pod {{ $labels.pod }} is crash-looping"
          description: "{{ $labels.pod }} has restarted {{ $value | humanize }} times in the last 15 minutes"

      - alert: DatabaseConnectionFailed
        expr: pg_up{job="postgres"} == 0
        for: 2m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "PostgreSQL is unreachable"
          description: "Nexora PostgreSQL has been unreachable for more than 2 minutes."

      - alert: KafkaConsumerLag
        expr: kafka_consumer_group_lag{group="nexora-workers"} > 1000
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Kafka consumer lag is high"
          description: "nexora-workers consumer group lag is {{ $value | humanize }} messages"

      - alert: KafkaBrokerDown
        expr: kafka_brokers{job="kafka"} == 0
        for: 2m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Kafka broker is down"
          description: "No Kafka brokers available. API running in dry-run mode."

  - name: nexora.application
    interval: 60s
    rules:
      - alert: LlmHighFallbackRate
        expr: |
          (
            rate(nexora_llm_fallbacks_total[10m])
            /
            (rate(nexora_llm_calls_total[10m]) + rate(nexora_llm_fallbacks_total[10m]) + 0.001)
          ) > 0.30
        for: 10m
        labels:
          severity: warning
          team: ml
        annotations:
          summary: "High LLM fallback rate"
          description: "LLM fallback rate is {{ $value | humanizePercentage }}. Customers receiving holding messages."

      - alert: LlmAllFallback
        expr: |
          (
            rate(nexora_llm_fallbacks_total[5m])
            /
            (rate(nexora_llm_calls_total[5m]) + rate(nexora_llm_fallbacks_total[5m]) + 0.001)
          ) > 0.99
        for: 5m
        labels:
          severity: critical
          team: ml
        annotations:
          summary: "LLM provider appears completely unavailable"
          description: "All LLM calls are falling back. Check provider status and API keys."

      - alert: EscalationRateHigh
        expr: |
          (
            rate(nexora_escalations_total[30m])
            /
            (rate(nexora_tickets_created_total[30m]) + 0.001)
          ) > 0.20
        for: 30m
        labels:
          severity: warning
          team: customer-success
        annotations:
          summary: "High escalation rate detected"
          description: "Escalation rate is {{ $value | humanizePercentage }} (threshold: 20%)"

      - alert: WebhookGmailFailures
        expr: |
          (
            rate(http_requests_total{path="/webhooks/gmail",status!="200"}[5m])
            /
            (rate(http_requests_total{path="/webhooks/gmail"}[5m]) + 0.001)
          ) > 0.10
        for: 5m
        labels:
          severity: warning
          team: integrations
        annotations:
          summary: "Gmail webhook returning errors"
          description: "Gmail webhook non-200 rate: {{ $value | humanizePercentage }}"
```
