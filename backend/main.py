"""
Nexora Customer Success Digital FTE — Backend Entry Point (Stage 3)

This is the canonical entry point for the FastAPI application.

Run locally:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Run in Docker / production:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1

Hugging Face Spaces (Dockerfile-based):
    CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
    (HF Spaces exposes port 7860 by default)

The FastAPI app is defined in backend/api/main.py and re-exported here
so tooling and deployment configs only need to reference one stable path.
"""

from backend.api.main import app  # noqa: F401 — re-export for uvicorn

__all__ = ["app"]
