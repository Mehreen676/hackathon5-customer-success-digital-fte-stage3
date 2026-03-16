"""
Database Engine — Customer Success Digital FTE (Stage 2)

Default: SQLite for development (no server required).
Production: Set DATABASE_URL environment variable to a PostgreSQL DSN.

  Example:
    DATABASE_URL=postgresql://user:password@localhost:5432/nexora_support
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "sqlite:///./nexora_support.db",
)

# SQLite requires check_same_thread=False; PostgreSQL does not
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Declarative base — all ORM models inherit from this
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db():
    """
    FastAPI dependency that yields a database session and closes it
    after the request completes (whether successful or not).

    Usage in route:
        @router.post("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Create all database tables. Safe to call on every startup — SQLAlchemy
    uses CREATE TABLE IF NOT EXISTS, so existing tables are never dropped.
    """
    from backend.database import models  # noqa: F401 — registers models with Base
    Base.metadata.create_all(bind=engine)
