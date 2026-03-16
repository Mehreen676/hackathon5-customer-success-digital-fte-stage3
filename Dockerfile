# ============================================================
# Nexora Customer Success Digital FTE — Dockerfile
# Stage 3 | Author: Mehreen Asghar | Hackathon 5
# ============================================================
#
# Multi-stage build:
#   stage 1 (builder) — install Python deps into a virtual-env
#   stage 2 (runtime) — copy only the venv + source, no build tools
#
# Build:
#   docker build -t nexora-cs-fte:3.0.0 .
#
# Run API server:
#   docker run -p 8000:8000 --env-file .env nexora-cs-fte:3.0.0
#
# Run message-processor worker:
#   docker run --env-file .env nexora-cs-fte:3.0.0 \
#     python -m workers.message_processor
#
# Run retry worker:
#   docker run --env-file .env nexora-cs-fte:3.0.0 \
#     python -m workers.retry_worker
#
# Hugging Face Spaces (container SDK):
#   Set APP_PORT=7860 in Space settings — HF exposes 7860 by default.
#   uvicorn backend.main:app --host 0.0.0.0 --port 7860
# ============================================================

# ── Stage 1: dependency builder ──────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps needed to compile any C extensions (confluent-kafka, psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        librdkafka-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir confluent-kafka==2.4.0

# ── Stage 2: production runtime ──────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user for security
RUN groupadd --gid 1001 nexora && \
    useradd  --uid 1001 --gid nexora --shell /bin/bash --create-home nexora

# Runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        librdkafka1 \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY --chown=nexora:nexora backend/   ./backend/
COPY --chown=nexora:nexora workers/   ./workers/
COPY --chown=nexora:nexora context/   ./context/
COPY --chown=nexora:nexora startup.sh ./startup.sh

RUN chmod +x ./startup.sh

# Switch to non-root user
USER nexora

# Expose FastAPI port
EXPOSE 8000

# Health check — polls /health every 30s
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: start the API server
CMD ["./startup.sh"]
