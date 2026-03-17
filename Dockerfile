# ============================================================
# Nexora Customer Success Digital FTE — Hugging Face Spaces
# Stage 3 | Author: Mehreen Asghar | Hackathon 5
#
# Port 7860 is required by Hugging Face Spaces (Docker SDK).
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# Install minimal system deps (curl for health check only)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY backend/ ./backend/
COPY context/ ./context/

# Ensure the working directory is writable for the SQLite database file
RUN chmod -R 777 /app

# Expose Hugging Face Spaces required port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start FastAPI on port 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
