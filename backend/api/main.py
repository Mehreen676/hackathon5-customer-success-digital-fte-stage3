"""
FastAPI Application — Customer Success Digital FTE (Stage 3)

Entry point for the Stage 3 backend service with AI reasoning layer.

Run with:
    uvicorn src.api.main:app --reload

Swagger UI:
    http://localhost:8000/docs

ReDoc:
    http://localhost:8000/redoc
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.analytics import router as analytics_router
from backend.api.health import router as health_router
from backend.api.support_api import router as support_router
from backend.api.webhooks import router as webhooks_router
from backend.database.database import init_db, SessionLocal
from backend.mcp.tool_registry import init_tools
from backend.services.knowledge_service import seed_all

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle manager.

    Startup:
        1. Create all database tables (idempotent)
        2. Register all MCP tools
        3. Seed knowledge base and sample customers (idempotent)

    Shutdown:
        Nothing to teardown in Stage 2 (connection pool handled by SQLAlchemy).
    """
    logger.info("=== Nexora Customer Success Agent — Stage 3 Starting ===")

    # Step 1: Initialize database schema
    logger.info("Initializing database schema...")
    init_db()

    # Step 2: Register MCP tools
    logger.info("Registering MCP tools...")
    init_tools()

    # Step 3: Seed initial data
    logger.info("Seeding initial data...")
    db = SessionLocal()
    try:
        seed_result = seed_all(db)
        logger.info(
            "Data seed complete: %d KB entries, %d customers",
            seed_result["kb_entries_seeded"],
            seed_result["customers_seeded"],
        )
    finally:
        db.close()

    logger.info("=== Service ready — Stage 3 AI reasoning active ===")
    yield
    logger.info("=== Nexora Customer Success Agent — Stage 3 Shutting Down ===")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Nexora Customer Success Digital FTE",
    description=(
        "Stage 3 full-system AI Customer Success agent. "
        "Handles inbound support messages from Email, WhatsApp, and Web Form channels. "
        "Processes messages through a 10-step AI-augmented workflow with database persistence, "
        "escalation detection, knowledge base search, LLM response generation, "
        "ticket creation, and analytics tracking.\n\n"
        "**Hackathon 5 | Stage 3 | Project Owner: Mehreen Asghar**"
    ),
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS middleware — allow all origins in development
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

app.include_router(health_router)
app.include_router(support_router)
app.include_router(analytics_router)
app.include_router(webhooks_router)


# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "Nexora Customer Success Digital FTE",
        "stage": "3",
        "version": "3.0.0",
        "docs": "/docs",
        "health": "/health",
        "analytics": "/analytics/summary",
        "author": "Mehreen Asghar",
        "hackathon": "Hackathon 5",
    }
