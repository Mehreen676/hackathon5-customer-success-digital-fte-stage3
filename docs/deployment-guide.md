# Deployment Guide — Nexora Customer Success Digital FTE (Stage 3)

**Project Owner:** Mehreen Asghar
**Last Updated:** 2025-01-01

---

## Prerequisites

| Tool | Minimum Version | Purpose |
|------|----------------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| Docker | 24+ | Container runtime |
| docker-compose | 2.20+ | Local multi-service stack |
| kubectl | 1.28+ | Kubernetes deployment |
| PostgreSQL | 15+ | Production database |

---

## 1. Local Development (No Docker)

### 1.1 Backend

```bash
# Clone and enter project
cd hackathon5-customer-success-digital-fte-stage3

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — see Environment Variables section below

# Seed the database (idempotent)
python -m src.db.seed

# Start the API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Backend is now accessible at `http://localhost:8000`.
API docs: `http://localhost:8000/docs`

### 1.2 Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend is now accessible at `http://localhost:3000`.

### 1.3 Verify

```bash
# Health check
curl http://localhost:8000/health

# Analytics summary
curl http://localhost:8000/analytics/summary

# Submit a test message
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","subject":"Test","message":"Hello"}'
```

---

## 2. Docker Compose (Recommended for Local Full-Stack)

```bash
# Build and start all services
docker-compose up --build

# Start in background
docker-compose up -d --build

# View logs
docker-compose logs -f api
docker-compose logs -f worker-retry
docker-compose logs -f kafka

# Stop all services
docker-compose down

# Stop and remove volumes (resets the database)
docker-compose down -v
```

Services started by `docker-compose up`:

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI backend |
| `frontend` | 3000 | Next.js dashboard |
| `postgres` | 5432 | PostgreSQL database |
| `zookeeper` | 2181 | Kafka dependency |
| `kafka` | 9092 | Event streaming |
| `redis` | 6379 | Cache / rate-limiting |
| `worker-retry` | — | Dead-letter retry worker |
| `worker-metrics` | — | Metrics aggregation worker |

### 2.1 First-Time Setup

```bash
# Wait for services to be healthy, then seed the database
docker-compose exec api python -m src.db.seed
```

### 2.2 Environment Variables

Create `.env` in the project root:

```bash
# Database
DATABASE_URL=postgresql://nexora:nexora@postgres:5432/nexora_cs

# LLM Provider (pick one)
LLM_PROVIDER=anthropic          # anthropic | openai | gemini
LLM_MODEL=claude-sonnet-4-6     # leave blank for provider default
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_AI_API_KEY=AIza...

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Gmail Integration (optional — runs in MOCK mode without these)
GMAIL_CREDENTIALS_PATH=/run/secrets/gmail_credentials.json
GMAIL_TOPIC_NAME=projects/nexora/topics/gmail-push

# Twilio / WhatsApp (optional — runs in MOCK mode without these)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Application
CORS_ORIGINS=http://localhost:3000,https://your-domain.com
LOG_LEVEL=INFO
```

---

## 3. Kubernetes Deployment

### 3.1 Apply Manifests

```bash
# Create namespace
kubectl create namespace nexora

# Apply all manifests
kubectl apply -f k8s/ -n nexora

# Check rollout status
kubectl rollout status deployment/nexora-api -n nexora
kubectl rollout status deployment/nexora-frontend -n nexora
```

### 3.2 Manifest Structure

```
k8s/
├── namespace.yaml          — nexora namespace
├── configmap.yaml          — non-secret environment variables
├── secrets.yaml            — API keys, DB credentials (base64)
├── postgres/
│   ├── deployment.yaml     — PostgreSQL StatefulSet
│   └── service.yaml        — ClusterIP service
├── kafka/
│   ├── deployment.yaml     — Kafka + Zookeeper
│   └── service.yaml
├── api/
│   ├── deployment.yaml     — FastAPI (3 replicas)
│   ├── service.yaml        — ClusterIP port 8000
│   ├── hpa.yaml            — HPA: 3–10 pods, 70% CPU
│   └── ingress.yaml        — NGINX ingress
├── frontend/
│   ├── deployment.yaml     — Next.js (2 replicas)
│   ├── service.yaml
│   └── ingress.yaml
└── workers/
    ├── retry-worker.yaml   — Dead-letter retry worker
    └── metrics-worker.yaml — Metrics aggregation worker
```

### 3.3 Secrets Setup

```bash
# Create secrets from .env values (never commit secrets to git)
kubectl create secret generic nexora-secrets \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  --from-literal=TWILIO_AUTH_TOKEN=xxx \
  --from-literal=POSTGRES_PASSWORD=strongpassword \
  -n nexora
```

### 3.4 Scale Manually

```bash
# Scale API replicas
kubectl scale deployment nexora-api --replicas=5 -n nexora

# View HPA status
kubectl get hpa -n nexora
```

### 3.5 Rolling Update

```bash
# Build and push new image
docker build -t your-registry/nexora-api:v3.1.0 .
docker push your-registry/nexora-api:v3.1.0

# Apply new image
kubectl set image deployment/nexora-api \
  api=your-registry/nexora-api:v3.1.0 \
  -n nexora

# Monitor rollout
kubectl rollout status deployment/nexora-api -n nexora

# Rollback if needed
kubectl rollout undo deployment/nexora-api -n nexora
```

---

## 4. Database Migrations

```bash
# Run migrations (Alembic)
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "add_new_column"

# Rollback one step
alembic downgrade -1
```

If Alembic is not yet configured, use the idempotent seed script:

```bash
python -m src.db.seed
```

---

## 5. Frontend Build (Production)

```bash
cd frontend

# Install and build
npm ci
npm run build

# Start production server
npm start

# Or export as static files
npm run export
```

The Next.js frontend proxies `/api/backend/*` to the FastAPI backend (configured in `next.config.js`).

---

## 6. Worker Processes

Workers are separate Python processes that consume Kafka topics:

```bash
# Retry worker (processes dead-letter messages)
python workers/retry_worker.py

# Metrics worker (aggregates analytics from Kafka)
python workers/metrics_worker.py
```

In Docker Compose these start automatically.
In Kubernetes they run as separate Deployments in `k8s/workers/`.

---

## 7. Health Checks & Readiness

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness check — returns `{"status": "ok"}` |
| `GET /health/ready` | Readiness check — verifies DB connection |
| `GET /analytics/summary` | Smoke test for analytics pipeline |

Kubernetes uses these for liveness and readiness probes (configured in `k8s/api/deployment.yaml`).

---

## 8. Troubleshooting

### Backend won't start

```bash
# Check for import errors
python -c "from src.api.main import app; print('OK')"

# Check DB connection
python -c "from src.db.database import engine; engine.connect(); print('DB OK')"
```

### Kafka connection refused

```bash
# In docker-compose, wait for Kafka to be ready
docker-compose logs kafka | grep "started"

# Test connectivity
docker-compose exec api python -c "
from src.kafka.producer import KafkaEventProducer
p = KafkaEventProducer()
print('dry_run' if p.dry_run else 'connected')
"
```

### LLM API key not working

The system falls back gracefully — check the log output for:
```
LLM fallback: ...
```

Set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=your-key` in `.env`.

### Frontend shows "Backend Offline"

1. Confirm API is running: `curl http://localhost:8000/health`
2. Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
3. Confirm CORS: `CORS_ORIGINS` includes `http://localhost:3000`
