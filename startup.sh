#!/usr/bin/env bash
# ============================================================
# Nexora Customer Success Digital FTE — Startup Script
# Runs database migrations and starts the FastAPI server
# ============================================================

set -euo pipefail

LOG_LEVEL="${LOG_LEVEL:-INFO}"
APP_PORT="${APP_PORT:-8000}"
APP_HOST="${APP_HOST:-0.0.0.0}"
WORKERS="${UVICORN_WORKERS:-1}"

echo "======================================================"
echo " Nexora Customer Success Digital FTE — Stage 3"
echo " Starting at $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "======================================================"

# ── Wait for PostgreSQL if DATABASE_URL is a postgres:// URI ──
if [[ "${DATABASE_URL:-}" == postgresql* ]]; then
  echo "[startup] Waiting for PostgreSQL..."
  # Extract host and port from DATABASE_URL
  DB_HOST=$(echo "$DATABASE_URL" | sed -E 's|.*@([^:/]+).*|\1|')
  DB_PORT=$(echo "$DATABASE_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
  DB_PORT="${DB_PORT:-5432}"

  MAX_WAIT=60
  ELAPSED=0
  until python -c "
import socket, sys
try:
    socket.create_connection(('${DB_HOST}', ${DB_PORT}), timeout=2)
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
      echo "[startup] ERROR: PostgreSQL not available after ${MAX_WAIT}s — aborting."
      exit 1
    fi
    echo "[startup] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}... (${ELAPSED}s)"
    sleep 2
    ELAPSED=$((ELAPSED + 2))
  done
  echo "[startup] PostgreSQL is ready."
fi

# ── Wait for Kafka if KAFKA_BOOTSTRAP_SERVERS is set ──────────
if [[ -n "${KAFKA_BOOTSTRAP_SERVERS:-}" ]]; then
  echo "[startup] Waiting for Kafka at ${KAFKA_BOOTSTRAP_SERVERS}..."
  KAFKA_HOST=$(echo "$KAFKA_BOOTSTRAP_SERVERS" | cut -d: -f1)
  KAFKA_PORT=$(echo "$KAFKA_BOOTSTRAP_SERVERS" | cut -d: -f2)

  MAX_WAIT=60
  ELAPSED=0
  until python -c "
import socket, sys
try:
    socket.create_connection(('${KAFKA_HOST}', ${KAFKA_PORT}), timeout=2)
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
      echo "[startup] WARNING: Kafka not reachable — starting without Kafka (dry-run mode)."
      break
    fi
    echo "[startup] Waiting for Kafka... (${ELAPSED}s)"
    sleep 2
    ELAPSED=$((ELAPSED + 2))
  done
  echo "[startup] Kafka check complete."
fi

# ── Initialise database (idempotent) ──────────────────────────
echo "[startup] Initialising database schema..."
python -c "
from backend.database.database import init_db
init_db()
print('[startup] Database schema ready.')
"

# ── Seed initial data ──────────────────────────────────────────
echo "[startup] Seeding knowledge base and sample customers..."
python -c "
from backend.database.database import SessionLocal
from backend.services.knowledge_service import seed_all
db = SessionLocal()
try:
    result = seed_all(db)
    print(f'[startup] Seeded: {result[\"kb_entries_seeded\"]} KB entries, {result[\"customers_seeded\"]} customers')
finally:
    db.close()
"

# ── Start FastAPI with uvicorn ─────────────────────────────────
echo "[startup] Starting FastAPI on ${APP_HOST}:${APP_PORT} (workers=${WORKERS})..."
exec uvicorn backend.main:app \
  --host "${APP_HOST}" \
  --port "${APP_PORT}" \
  --workers "${WORKERS}" \
  --log-level "$(echo ${LOG_LEVEL} | tr '[:upper:]' '[:lower:]')" \
  --access-log
