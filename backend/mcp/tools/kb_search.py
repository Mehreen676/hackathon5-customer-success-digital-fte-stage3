"""
MCP Tool: search_kb

Searches the database knowledge base for content relevant to the query.
Falls back to the Stage 1 in-memory KB if the database has no entries.

Registered as: "search_kb"
"""

import logging

from sqlalchemy.orm import Session

from backend.mcp.tool_registry import register

logger = logging.getLogger(__name__)


@register("search_kb")
def search_kb(query: str, db: Session, max_results: int = 3) -> dict:
    """
    Search the knowledge base for content relevant to the query.

    Args:
        query: The customer's question or message text.
        db: SQLAlchemy database session.
        max_results: Maximum number of results to return.

    Returns:
        dict:
            matched (bool)     — True if at least one result found
            results (list)     — List of {topic, content, category, score}
            query (str)        — The original query
            source (str)       — "database" or "fallback"
    """
    from backend.database import crud

    results = crud.search_kb_entries(db, query, max_results)

    if results:
        logger.info("KB search matched %d result(s) from database for query: %s", len(results), query[:60])
        return {
            "matched": True,
            "results": results,
            "query": query,
            "source": "database",
        }

    # Fallback to Stage 1 in-memory KB
    logger.info("DB KB empty — falling back to Stage 1 in-memory KB for: %s", query[:60])
    return _fallback_search(query, max_results)


def _fallback_search(query: str, max_results: int) -> dict:
    """Stage 1 in-memory KB search — used when database is empty."""
    from backend.services.knowledge_service import KNOWLEDGE_BASE_SEED

    query_lower = query.lower()
    query_words = set(query_lower.split())
    scored = []

    for entry in KNOWLEDGE_BASE_SEED:
        match_score = sum(1 for kw in entry["keywords"] if kw in query_lower)
        keyword_words = set(" ".join(entry["keywords"]).split())
        word_overlap = len(query_words & keyword_words)
        total = match_score + (word_overlap * 0.5)
        if total > 0:
            scored.append((total, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [
        {
            "topic": e["topic"],
            "content": e["content"],
            "category": "general",
            "score": score,
        }
        for score, e in scored[:max_results]
    ]

    return {
        "matched": len(results) > 0,
        "results": results,
        "query": query,
        "source": "fallback",
    }
