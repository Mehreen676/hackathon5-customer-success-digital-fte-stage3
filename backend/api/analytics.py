"""
Analytics API — Nexora Customer Success Digital FTE (Stage 3).

Exposes agent metrics and LLM usage data to the frontend dashboard.

Endpoints:
    GET /analytics/summary     — aggregate KPIs
    GET /analytics/usage       — LLM token usage and cost breakdown
    GET /analytics/recent      — recent interaction log
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_metrics_summary() -> Dict[str, Any]:
    """Return metrics summary, or a demo snapshot if no data recorded yet."""
    try:
        from backend.analytics.agent_metrics import metrics_collector  # noqa: PLC0415

        summary = metrics_collector.get_summary()

        if summary.total_interactions == 0:
            return _demo_summary()

        return {
            "total_interactions": summary.total_interactions,
            "avg_response_time_ms": summary.avg_response_time_ms,
            "escalation_rate": summary.escalation_rate,
            "kb_hit_rate": summary.kb_hit_rate,
            "ai_usage_rate": summary.ai_usage_rate,
            "fallback_rate": summary.fallback_rate,
            "ticket_creation_rate": summary.ticket_creation_rate,
            "interactions_by_channel": summary.interactions_by_channel,
            "interactions_by_intent": summary.interactions_by_intent,
            "interactions_by_source": summary.interactions_by_source,
            "total_tokens_used": summary.total_tokens_used,
            "period_start": summary.period_start,
            "period_end": summary.period_end,
            "source": "live",
        }

    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load live metrics: %s — returning demo data", exc)
        return _demo_summary()


def _demo_summary() -> Dict[str, Any]:
    """Return a realistic demo snapshot for the dashboard preview."""
    return {
        "total_interactions": 1247,
        "avg_response_time_ms": 342.5,
        "escalation_rate": 0.12,
        "kb_hit_rate": 0.68,
        "ai_usage_rate": 0.20,
        "fallback_rate": 0.08,
        "ticket_creation_rate": 0.94,
        "interactions_by_channel": {
            "email": 587,
            "whatsapp": 412,
            "web_form": 248,
        },
        "interactions_by_intent": {
            "billing": 312,
            "account": 287,
            "integration": 198,
            "general": 176,
            "plan": 143,
            "data": 67,
            "team": 64,
        },
        "interactions_by_source": {
            "kb": 848,
            "llm": 249,
            "fallback": 100,
            "escalation": 50,
        },
        "total_tokens_used": 284500,
        "period_start": "2026-03-01T00:00:00+00:00",
        "period_end": "2026-03-14T23:59:59+00:00",
        "source": "demo",
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/summary")
def get_analytics_summary() -> Dict[str, Any]:
    """
    Return aggregate KPI summary for the frontend dashboard.

    Returns live data if interactions have been recorded, otherwise falls
    back to a pre-populated demo snapshot so the dashboard always renders.
    """
    return _get_metrics_summary()


@router.get("/usage")
def get_usage_stats() -> Dict[str, Any]:
    """
    Return LLM token consumption and estimated cost breakdown.

    Includes per-provider aggregates and daily usage trend.
    """
    try:
        from backend.analytics.usage_tracking import usage_tracker  # noqa: PLC0415

        total_cost = usage_tracker.get_total_cost()
        total_tokens = usage_tracker.get_total_tokens()
        by_provider = {
            p: {
                "total_calls": s.total_calls,
                "total_input_tokens": s.total_input_tokens,
                "total_output_tokens": s.total_output_tokens,
                "total_tokens": s.total_tokens,
                "total_cost_usd": s.total_cost_usd,
                "models_used": s.models_used,
            }
            for p, s in usage_tracker.get_usage_by_provider().items()
        }
        daily = [
            {"date": d.date, "total_calls": d.total_calls,
             "total_tokens": d.total_tokens, "total_cost_usd": d.total_cost_usd}
            for d in usage_tracker.get_daily_usage()
        ]

        if not by_provider:
            return _demo_usage()

        return {
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "by_provider": by_provider,
            "daily_trend": daily,
            "source": "live",
        }

    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load usage stats: %s", exc)
        return _demo_usage()


def _demo_usage() -> Dict[str, Any]:
    return {
        "total_cost_usd": 0.8432,
        "total_tokens": 284500,
        "by_provider": {
            "anthropic": {
                "total_calls": 249,
                "total_input_tokens": 127800,
                "total_output_tokens": 87200,
                "total_tokens": 215000,
                "total_cost_usd": 0.6918,
                "models_used": ["claude-sonnet-4-6"],
            }
        },
        "daily_trend": [
            {"date": "2026-03-12", "total_calls": 87, "total_tokens": 94200, "total_cost_usd": 0.2814},
            {"date": "2026-03-13", "total_calls": 94, "total_tokens": 101800, "total_cost_usd": 0.3046},
            {"date": "2026-03-14", "total_calls": 68, "total_tokens": 88500, "total_cost_usd": 0.2572},
        ],
        "source": "demo",
    }


@router.get("/recent")
def get_recent_interactions(limit: int = 20) -> Dict[str, Any]:
    """
    Return the most recent N interaction records.

    Useful for the live feed panel in the dashboard.
    """
    try:
        from backend.analytics.agent_metrics import metrics_collector  # noqa: PLC0415

        records = metrics_collector.get_recent(limit=min(limit, 100))
        if not records:
            return {"records": _demo_recent(), "source": "demo"}
        return {"records": records, "source": "live"}

    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load recent interactions: %s", exc)
        return {"records": _demo_recent(), "source": "demo"}


def _demo_recent() -> list:
    return [
        {
            "interaction_id": "conv-001",
            "channel": "email",
            "intent": "billing",
            "response_source": "kb",
            "response_time_ms": 187.3,
            "escalated": False,
            "kb_used": True,
            "ai_used": False,
            "ticket_created": True,
            "tokens_used": 0,
            "timestamp": "2026-03-14T10:23:15+00:00",
        },
        {
            "interaction_id": "conv-002",
            "channel": "whatsapp",
            "intent": "account",
            "response_source": "llm",
            "response_time_ms": 1243.8,
            "escalated": False,
            "kb_used": False,
            "ai_used": True,
            "ticket_created": True,
            "tokens_used": 847,
            "timestamp": "2026-03-14T10:19:42+00:00",
        },
        {
            "interaction_id": "conv-003",
            "channel": "web_form",
            "intent": "refund",
            "response_source": "escalation",
            "response_time_ms": 234.1,
            "escalated": True,
            "kb_used": False,
            "ai_used": False,
            "ticket_created": True,
            "tokens_used": 0,
            "timestamp": "2026-03-14T10:11:07+00:00",
        },
    ]
