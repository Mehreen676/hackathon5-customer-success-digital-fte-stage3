"""
Agent Metrics Collector — Nexora Customer Success Digital FTE (Stage 3).

Tracks per-interaction performance data in memory and persists to a JSON file.
Provides summary statistics for the analytics dashboard.

Usage::

    from backend.analytics.agent_metrics import metrics_collector

    metrics_collector.record_interaction(
        interaction_id="conv-abc123",
        channel="email",
        intent="billing",
        response_source="kb",
        response_time_ms=234.5,
        escalated=False,
        kb_used=True,
        ai_used=False,
        ticket_created=True,
    )

    summary = metrics_collector.get_summary()
    print(summary.total_interactions)
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_METRICS_FILE = Path("metrics_store.json")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class InteractionRecord:
    """One processed message."""

    interaction_id: str
    channel: str
    intent: str
    response_source: str          # "kb" | "llm" | "fallback" | "escalation"
    response_time_ms: float
    escalated: bool
    kb_used: bool
    ai_used: bool
    ticket_created: bool
    tokens_used: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class MetricsSummary:
    """Aggregate statistics across all recorded interactions."""

    total_interactions: int
    avg_response_time_ms: float
    escalation_rate: float          # 0.0 – 1.0
    kb_hit_rate: float
    ai_usage_rate: float
    fallback_rate: float
    ticket_creation_rate: float
    interactions_by_channel: Dict[str, int]
    interactions_by_intent: Dict[str, int]
    interactions_by_source: Dict[str, int]
    total_tokens_used: int
    period_start: Optional[str]
    period_end: Optional[str]


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------


class MetricsCollector:
    """
    Thread-safe, singleton-friendly metrics collector.

    All recorded interactions are kept in memory and also flushed to
    ``metrics_store.json`` for cross-process persistence.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._interactions: List[InteractionRecord] = []
        self._load_from_disk()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_interaction(
        self,
        interaction_id: str,
        channel: str,
        intent: str,
        response_source: str,
        response_time_ms: float,
        escalated: bool,
        kb_used: bool,
        ai_used: bool,
        ticket_created: bool,
        tokens_used: int = 0,
    ) -> None:
        """
        Record one completed interaction.

        Args:
            interaction_id: Conversation or message UUID.
            channel: "email" | "whatsapp" | "web_form".
            intent: Classified intent label.
            response_source: "kb" | "llm" | "fallback" | "escalation".
            response_time_ms: End-to-end pipeline latency.
            escalated: Whether the issue was escalated.
            kb_used: Whether KB returned a match.
            ai_used: Whether the LLM was invoked.
            ticket_created: Whether a ticket was opened.
            tokens_used: LLM tokens consumed (0 if not applicable).
        """
        record = InteractionRecord(
            interaction_id=interaction_id,
            channel=channel,
            intent=intent,
            response_source=response_source,
            response_time_ms=response_time_ms,
            escalated=escalated,
            kb_used=kb_used,
            ai_used=ai_used,
            ticket_created=ticket_created,
            tokens_used=tokens_used,
        )

        with self._lock:
            self._interactions.append(record)

        self._persist_async(record)
        logger.debug("Metric recorded | %s | %s | %.1fms", channel, intent, response_time_ms)

    def get_summary(self) -> MetricsSummary:
        """Compute and return aggregate statistics."""
        with self._lock:
            interactions = list(self._interactions)

        total = len(interactions)
        if total == 0:
            return MetricsSummary(
                total_interactions=0,
                avg_response_time_ms=0.0,
                escalation_rate=0.0,
                kb_hit_rate=0.0,
                ai_usage_rate=0.0,
                fallback_rate=0.0,
                ticket_creation_rate=0.0,
                interactions_by_channel={},
                interactions_by_intent={},
                interactions_by_source={},
                total_tokens_used=0,
                period_start=None,
                period_end=None,
            )

        avg_rt = sum(r.response_time_ms for r in interactions) / total
        esc_rate = sum(1 for r in interactions if r.escalated) / total
        kb_rate = sum(1 for r in interactions if r.kb_used) / total
        ai_rate = sum(1 for r in interactions if r.ai_used) / total
        fallback_rate = sum(1 for r in interactions if r.response_source == "fallback") / total
        ticket_rate = sum(1 for r in interactions if r.ticket_created) / total
        total_tokens = sum(r.tokens_used for r in interactions)

        by_channel: Dict[str, int] = {}
        by_intent: Dict[str, int] = {}
        by_source: Dict[str, int] = {}

        for r in interactions:
            by_channel[r.channel] = by_channel.get(r.channel, 0) + 1
            by_intent[r.intent] = by_intent.get(r.intent, 0) + 1
            by_source[r.response_source] = by_source.get(r.response_source, 0) + 1

        timestamps = sorted(r.timestamp for r in interactions)
        return MetricsSummary(
            total_interactions=total,
            avg_response_time_ms=round(avg_rt, 2),
            escalation_rate=round(esc_rate, 4),
            kb_hit_rate=round(kb_rate, 4),
            ai_usage_rate=round(ai_rate, 4),
            fallback_rate=round(fallback_rate, 4),
            ticket_creation_rate=round(ticket_rate, 4),
            interactions_by_channel=by_channel,
            interactions_by_intent=by_intent,
            interactions_by_source=by_source,
            total_tokens_used=total_tokens,
            period_start=timestamps[0] if timestamps else None,
            period_end=timestamps[-1] if timestamps else None,
        )

    def get_recent(self, limit: int = 20) -> List[dict]:
        """Return the most recent N interaction records as plain dicts."""
        with self._lock:
            recent = self._interactions[-limit:][::-1]
        return [asdict(r) for r in recent]

    def reset(self) -> None:
        """Clear all in-memory metrics (does NOT delete the disk file)."""
        with self._lock:
            self._interactions.clear()
        logger.info("MetricsCollector reset.")

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _persist_async(self, record: InteractionRecord) -> None:
        """Append the record to disk in a background thread."""
        t = threading.Thread(target=self._append_to_file, args=(record,), daemon=True)
        t.start()

    def _append_to_file(self, record: InteractionRecord) -> None:
        try:
            existing: list = []
            if _METRICS_FILE.exists():
                try:
                    existing = json.loads(_METRICS_FILE.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    existing = []

            existing.append(asdict(record))
            _METRICS_FILE.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not persist metric to disk: %s", exc)

    def _load_from_disk(self) -> None:
        """Load existing metrics from disk on startup."""
        if not _METRICS_FILE.exists():
            return
        try:
            data = json.loads(_METRICS_FILE.read_text(encoding="utf-8"))
            for item in data:
                try:
                    self._interactions.append(InteractionRecord(**item))
                except (TypeError, KeyError):
                    pass  # skip malformed entries
            logger.info("Loaded %d metrics from disk.", len(self._interactions))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load metrics from disk: %s", exc)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

metrics_collector = MetricsCollector()
