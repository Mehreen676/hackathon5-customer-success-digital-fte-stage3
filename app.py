"""
Hugging Face Spaces entry point — Nexora Customer Success Digital FTE (Stage 3)

Hugging Face Spaces exposes port 7860. This file makes the app discoverable
by both the HF Spaces runtime (which looks for app.py) and any tooling that
expects a top-level entry point.

Deploy on HF Spaces (Dockerfile-based):
    CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]

Or run directly:
    python app.py
"""

import os

from backend.api.main import app  # noqa: F401 — re-export

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
