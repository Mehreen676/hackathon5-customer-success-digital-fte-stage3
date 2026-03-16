# Runbook — Nexora Customer Success Digital FTE (Stage 3)

**Project Owner:** Mehreen Asghar
**Audience:** On-call engineers

This runbook covers incident response procedures for the Nexora Customer Success platform. Each section describes symptoms, diagnosis steps, and remediation actions.

---

## Table of Contents

1. [API Pod Restart / CrashLoopBackOff](#1-api-pod-restart--crashloopbackoff)
2. [Kafka Queue Backlog](#2-kafka-queue-backlog)
3. [Gmail Webhook Failures](#3-gmail-webhook-failures)
4. [WhatsApp Webhook Failures](#4-whatsapp-webhook-failures)
5. [Database Connection Issues](#5-database-connection-issues)
6. [LLM Provider Outage](#6-llm-provider-outage)
7. [Retry Worker Stalled](#7-retry-worker-stalled)
8. [High Response Latency](#8-high-response-latency)
9. [Frontend Offline](#9-frontend-offline)
10. [Analytics Data Missing](#10-analytics-data-missing)

---

## 1. API Pod Restart / CrashLoopBackOff

**Symptoms:** API pods cycling; `kubectl get pods` shows `CrashLoopBackOff` or `OOMKilled`.

### Diagnosis

```bash
# Check pod status
kubectl get pods -n nexora -l app=nexora-api

# Get crash reason
kubectl describe pod <pod-name> -n nexora

# View last N lines of crash logs
kubectl logs <pod-name> -n nexora --previous --tail=100
```

### Common Causes & Fixes

| Cause | Fix |
|-------|-----|
| Missing env var (DB URL, API key) | Add to `nexora-secrets` secret; rollout restart |
| OOMKilled | Increase memory limit in `k8s/api/deployment.yaml`; check for memory leaks |
| DB migration not run | `kubectl exec -it <pod> -- alembic upgrade head` |
| Import error in code | Deploy previous stable image tag |

### Rollback

```bash
kubectl rollout undo deployment/nexora-api -n nexora
kubectl rollout status deployment/nexora-api -n nexora
```

---

## 2. Kafka Queue Backlog

**Symptoms:** `analytics/summary` shows increasing pending counts; worker logs show lag.

### Diagnosis

```bash
# Check consumer group lag
kubectl exec -it <kafka-pod> -n nexora -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group nexora-workers

# List topics and partition counts
kubectl exec -it <kafka-pod> -n nexora -- \
  kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### Remediation

**Scale up workers:**
```bash
kubectl scale deployment nexora-worker-retry --replicas=3 -n nexora
kubectl scale deployment nexora-worker-metrics --replicas=2 -n nexora
```

**Check if workers are healthy:**
```bash
kubectl get pods -n nexora -l app=nexora-worker-retry
kubectl logs -l app=nexora-worker-retry -n nexora --tail=50
```

**If Kafka itself is overwhelmed (broker disk full):**
```bash
# Increase retention to compress older data
kubectl exec -it <kafka-pod> -n nexora -- \
  kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --entity-type topics \
  --entity-name nexora.events.inbound \
  --add-config retention.bytes=1073741824
```

### Dry-Run Mode

If Kafka is unavailable, the API automatically runs in dry-run mode (events logged to stdout only). Check:
```bash
kubectl logs -l app=nexora-api -n nexora | grep "dry.run\|DRY"
```

---

## 3. Gmail Webhook Failures

**Symptoms:** Pub/Sub dashboard shows undelivered messages; no new Gmail tickets created.

### Diagnosis

```bash
# Check webhook endpoint reachability
curl -X POST https://api.your-domain.com/webhooks/gmail \
  -H "Content-Type: application/json" \
  -d '{"message":{"data":"","messageId":"test","publishTime":"2025-01-01T00:00:00Z"}}'
# Expected: HTTP 200

# Check API logs for gmail webhook errors
kubectl logs -l app=nexora-api -n nexora | grep "gmail\|webhook"
```

### Common Causes & Fixes

| Cause | Diagnosis | Fix |
|-------|-----------|-----|
| Pub/Sub push URL misconfigured | Check Google Cloud Console → Pub/Sub → Subscriptions | Update push endpoint URL |
| Missing Gmail credentials | Logs show `GmailClient: MOCK mode` | Mount `gmail_credentials.json` secret |
| Pub/Sub ack timeout (processing > 10s) | Consumer ack deadline exceeded | Increase `ackDeadlineSeconds` to 60 in subscription config |
| Base64 decode error | Logs show `parse_pubsub_notification failed` | Update webhook handler to handle new Pub/Sub format |

### Test Gmail Webhook Locally

```bash
python -c "
import base64, json, requests
data = json.dumps({
  'from_email': 'test@example.com',
  'subject': 'Test',
  'body': 'Test message',
  'message_id': 'test001'
})
encoded = base64.b64encode(data.encode()).decode()
payload = {'message': {'data': encoded, 'messageId': 'test001', 'publishTime': '2025-01-01T00:00:00Z'}}
r = requests.post('http://localhost:8000/webhooks/gmail', json=payload)
print(r.status_code, r.json())
"
```

### Recovery

Pub/Sub automatically retries unacknowledged messages. Once the endpoint is fixed, backlogged messages will reprocess automatically. If the backlog is too large:

```bash
# Seek subscription to current time (discard old messages)
gcloud pubsub subscriptions seek projects/PROJECT/subscriptions/gmail-push \
  --time=now
```

---

## 4. WhatsApp Webhook Failures

**Symptoms:** WhatsApp messages not creating tickets; Twilio console shows failed deliveries.

### Diagnosis

```bash
# Test the endpoint
curl -X POST http://localhost:8000/webhooks/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp%3A%2B15005550001&Body=test&MessageSid=SMtest001&AccountSid=AC123&To=whatsapp%3A%2B14155238886&NumMedia=0"
# Expected: HTTP 200, JSON with received=true

# Check logs
kubectl logs -l app=nexora-api -n nexora | grep "whatsapp\|twilio"
```

### Common Causes & Fixes

| Cause | Fix |
|-------|-----|
| Twilio signature validation failing | Ensure `TWILIO_AUTH_TOKEN` matches the account; or set to empty for dev |
| Webhook URL not HTTPS | Twilio requires HTTPS for production; set up TLS/Ingress |
| `whatsapp:` prefix not stripped | Check `parse_twilio_webhook` in `src/webhooks/whatsapp_webhook.py` |
| Phone number not in E.164 format | Twilio sends `whatsapp:+XXXXXXXXXX`; parser strips the prefix |

### Twilio Debug

1. Open Twilio Console → Monitor → Logs → Messaging
2. Find failed webhook attempts and check HTTP status returned
3. Click into a failed attempt to see exact request headers and body

---

## 5. Database Connection Issues

**Symptoms:** API returns 500 errors; logs show `sqlalchemy.exc.OperationalError`.

### Diagnosis

```bash
# Check PostgreSQL pod
kubectl get pods -n nexora -l app=postgres
kubectl logs -l app=postgres -n nexora --tail=50

# Test connection from API pod
kubectl exec -it <api-pod> -n nexora -- \
  python -c "from src.db.database import engine; engine.connect(); print('OK')"
```

### Common Causes & Fixes

| Cause | Fix |
|-------|-----|
| PostgreSQL pod down | `kubectl rollout restart deployment/postgres -n nexora` |
| Connection pool exhausted | Increase `pool_size` in `src/db/database.py`; scale down API replicas |
| DB migration not applied | `kubectl exec -it <api-pod> -- alembic upgrade head` |
| Disk full on PVC | Expand PVC or archive old data |
| Wrong `DATABASE_URL` | Check `nexora-secrets`; ensure host matches PostgreSQL service name |

### Emergency: Reset Connection Pool

```bash
# Restart API pods to reset SQLAlchemy connection pool
kubectl rollout restart deployment/nexora-api -n nexora
```

---

## 6. LLM Provider Outage

**Symptoms:** Responses say "holding message" or "a specialist will follow up"; `ai_used=false` in all responses.

### Diagnosis

```bash
# Check which provider is configured
kubectl exec -it <api-pod> -n nexora -- printenv LLM_PROVIDER LLM_MODEL

# Test LLM directly
kubectl exec -it <api-pod> -n nexora -- python -c "
from src.llm.llm_client import LLMClient
c = LLMClient()
r = c.generate('You are a helpful assistant.', 'Say hello.')
print(r)
"
```

### Fallback Behavior

The system is designed to **never crash on LLM failure**. When the LLM is unavailable:
- Tier 1 (KB hit) — unaffected
- Tier 2 (LLM) — fails gracefully
- Tier 3 (fallback) — polite holding message is sent
- Ticket status set to `pending_review` for human follow-up

### Switching Providers

```bash
# Switch from Anthropic to OpenAI
kubectl set env deployment/nexora-api \
  LLM_PROVIDER=openai \
  LLM_MODEL=gpt-4o-mini \
  -n nexora

# Verify
kubectl rollout status deployment/nexora-api -n nexora
```

### Provider Status Pages

- Anthropic: https://status.anthropic.com
- OpenAI: https://status.openai.com
- Google AI: https://status.cloud.google.com

---

## 7. Retry Worker Stalled

**Symptoms:** Dead-letter queue growing; messages in `nexora.events.dead_letter` topic not reprocessing.

### Diagnosis

```bash
# Check worker health
kubectl get pods -n nexora -l app=nexora-worker-retry
kubectl logs -l app=nexora-worker-retry -n nexora --tail=100

# Check dead-letter topic backlog
kubectl exec -it <kafka-pod> -n nexora -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group retry-worker-group
```

### Remediation

```bash
# Restart retry worker
kubectl rollout restart deployment/nexora-worker-retry -n nexora

# Scale up for faster catch-up
kubectl scale deployment nexora-worker-retry --replicas=3 -n nexora

# If messages keep failing (poison pill), reset consumer offset
kubectl exec -it <kafka-pod> -n nexora -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --reset-offsets --group retry-worker-group \
  --topic nexora.events.dead_letter \
  --to-latest --execute
```

---

## 8. High Response Latency

**Symptoms:** P95 latency > 2s; Prometheus alert `HighApiLatency` firing.

### Diagnosis

```bash
# Check current pod resource usage
kubectl top pods -n nexora -l app=nexora-api

# Check HPA status
kubectl get hpa -n nexora

# Identify slow endpoints
kubectl logs -l app=nexora-api -n nexora | grep "response_time_ms" | sort -t: -k2 -rn | head -20
```

### Triage Steps

1. **Is DB slow?** Check `EXPLAIN ANALYZE` on hot queries; verify indexes exist.
2. **Is LLM slow?** Check `ai_used` in responses — disable LLM temporarily if latency is unacceptable.
3. **Is Kafka slow?** Check producer lag in broker metrics.
4. **Are pods under-resourced?** Scale up or increase CPU/memory limits.

### Quick Mitigations

```bash
# Scale up API pods
kubectl scale deployment nexora-api --replicas=6 -n nexora

# Temporarily disable LLM to reduce latency
kubectl set env deployment/nexora-api LLM_PROVIDER=disabled -n nexora
```

---

## 9. Frontend Offline

**Symptoms:** Dashboard shows "Backend Offline"; all API calls return network errors.

### Diagnosis

```bash
# Check frontend pod
kubectl get pods -n nexora -l app=nexora-frontend

# Check API pod
kubectl get pods -n nexora -l app=nexora-api

# Check ingress
kubectl get ingress -n nexora
kubectl describe ingress nexora-ingress -n nexora
```

### Common Causes & Fixes

| Cause | Fix |
|-------|-----|
| API pod down | Restart API deployment |
| CORS misconfigured | Add frontend URL to `CORS_ORIGINS` env var |
| Ingress cert expired | Renew TLS cert; check cert-manager logs |
| `NEXT_PUBLIC_API_URL` wrong | Update configmap and restart frontend pods |

---

## 10. Analytics Data Missing

**Symptoms:** `GET /analytics/summary` returns demo/placeholder data; `recent` list is empty.

### Diagnosis

```bash
# Check analytics file
kubectl exec -it <api-pod> -n nexora -- \
  ls -la /app/data/metrics.json 2>/dev/null || echo "No metrics file"

# Check if analytics module is recording
kubectl logs -l app=nexora-api -n nexora | grep "analytics\|MetricsCollector"
```

### Notes

- Analytics uses a file-backed singleton (`MetricsCollector`) with JSON persistence.
- If the pod restarts, in-memory data is lost but `data/metrics.json` persists if a volume is mounted.
- The `/analytics/summary` endpoint returns demo data when no interactions have been processed yet.

### Fix: Mount Persistent Volume for Analytics

In `k8s/api/deployment.yaml`, add a volume mount for `/app/data/` pointing to a PersistentVolumeClaim.

---

## General Contact

- On-call rotation: check your incident management system
- Escalation path: `security_issue` → security-team; `legal_complaint` → legal-team
- Slack channel: `#nexora-ops` (if configured)
