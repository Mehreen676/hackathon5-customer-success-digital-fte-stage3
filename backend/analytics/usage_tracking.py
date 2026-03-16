"""
LLM Usage & Cost Tracker — Nexora Customer Success Digital FTE (Stage 3).

Tracks token consumption and estimated USD cost per LLM interaction.
Persists records to ``usage_log.json`` for billing visibility.

Usage::

    from backend.analytics.usage_tracking import usage_tracker

    record = usage_tracker.track_usage(
        provider="anthropic",
        model="claude-sonnet-4-6",
        input_tokens=512,
        output_tokens=256,
        interaction_id="conv-abc123",
    )
    print(f"Cost: ${record.cost_usd:.6f}")

    total = usage_tracker.get_total_cost()
    print(f"Total spend: ${total:.4f}")
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

_USAGE_FILE = Path("usage_log.json")

# ---------------------------------------------------------------------------
# Token cost table (USD per token)
# Update as provider pricing changes.
# ---------------------------------------------------------------------------

TOKEN_COSTS: Dict[str, Dict[str, float]] = {
    "anthropic/claude-sonnet-4-6": {"input": 0.000003, "output": 0.000015},
    "anthropic/claude-opus-4-6": {"input": 0.000015, "output": 0.000075},
    "anthropic/claude-haiku-4-5": {"input": 0.00000025, "output": 0.00000125},
    "openai/gpt-4o": {"input": 0.000005, "output": 0.000015},
    "openai/gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
    "openai/gpt-4-turbo": {"input": 0.00001, "output": 0.00003},
    "gemini/gemini-1.5-flash": {"input": 0.000000075, "output": 0.0000003},
    "gemini/gemini-1.5-pro": {"input": 0.0000035, "output": 0.0000105},
    # Fallback for unknown models
    "__default__": {"input": 0.000001, "output": 0.000002},
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class UsageRecord:
    """One LLM call's token consumption and cost."""

    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    interaction_id: Optional[str] = None


@dataclass
class ProviderUsageSummary:
    """Aggregated usage for a single provider."""

    provider: str
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_usd: float
    models_used: List[str]


@dataclass
class DailyUsage:
    """Usage aggregated by calendar day (UTC)."""

    date: str                  # YYYY-MM-DD
    total_calls: int
    total_tokens: int
    total_cost_usd: float


# ---------------------------------------------------------------------------
# UsageTracker
# ---------------------------------------------------------------------------


class UsageTracker:
    """
    Thread-safe LLM usage and cost tracker.

    Records every LLM API call with token counts and estimated cost.
    Persists to ``usage_log.json`` for cross-session reporting.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: List[UsageRecord] = []
        self._load_from_disk()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def track_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        interaction_id: Optional[str] = None,
    ) -> UsageRecord:
        """
        Record one LLM API call and compute its cost.

        Args:
            provider: "anthropic" | "openai" | "gemini".
            model: Model name (e.g. "claude-sonnet-4-6").
            input_tokens: Prompt token count.
            output_tokens: Completion token count.
            interaction_id: Optional link to a conversation/interaction ID.

        Returns:
            UsageRecord with computed cost_usd.
        """
        cost = self._compute_cost(provider, model, input_tokens, output_tokens)

        record = UsageRecord(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            interaction_id=interaction_id,
        )

        with self._lock:
            self._records.append(record)

        self._persist_async(record)
        logger.debug(
            "Usage tracked | %s/%s | in=%d out=%d | $%.6f",
            provider, model, input_tokens, output_tokens, cost,
        )
        return record

    def get_total_cost(self) -> float:
        """Return total USD spend across all recorded calls."""
        with self._lock:
            return round(sum(r.cost_usd for r in self._records), 6)

    def get_total_tokens(self) -> int:
        """Return total tokens (input + output) across all calls."""
        with self._lock:
            return sum(r.input_tokens + r.output_tokens for r in self._records)

    def get_usage_by_provider(self) -> Dict[str, ProviderUsageSummary]:
        """Return usage broken down by provider."""
        with self._lock:
            records = list(self._records)

        summaries: Dict[str, ProviderUsageSummary] = {}
        for r in records:
            p = r.provider
            if p not in summaries:
                summaries[p] = ProviderUsageSummary(
                    provider=p,
                    total_calls=0,
                    total_input_tokens=0,
                    total_output_tokens=0,
                    total_tokens=0,
                    total_cost_usd=0.0,
                    models_used=[],
                )
            s = summaries[p]
            s.total_calls += 1
            s.total_input_tokens += r.input_tokens
            s.total_output_tokens += r.output_tokens
            s.total_tokens += r.input_tokens + r.output_tokens
            s.total_cost_usd = round(s.total_cost_usd + r.cost_usd, 6)
            if r.model not in s.models_used:
                s.models_used.append(r.model)

        return summaries

    def get_daily_usage(self) -> List[DailyUsage]:
        """Return usage aggregated by UTC calendar day, sorted ascending."""
        with self._lock:
            records = list(self._records)

        daily: Dict[str, DailyUsage] = {}
        for r in records:
            day = r.timestamp[:10]  # "YYYY-MM-DD"
            if day not in daily:
                daily[day] = DailyUsage(date=day, total_calls=0, total_tokens=0, total_cost_usd=0.0)
            d = daily[day]
            d.total_calls += 1
            d.total_tokens += r.input_tokens + r.output_tokens
            d.total_cost_usd = round(d.total_cost_usd + r.cost_usd, 6)

        return sorted(daily.values(), key=lambda x: x.date)

    def get_recent_records(self, limit: int = 20) -> List[dict]:
        """Return the most recent N usage records as plain dicts."""
        with self._lock:
            recent = self._records[-limit:][::-1]
        return [asdict(r) for r in recent]

    def reset(self) -> None:
        """Clear in-memory records (does NOT delete the disk file)."""
        with self._lock:
            self._records.clear()

    # ------------------------------------------------------------------
    # Cost computation
    # ------------------------------------------------------------------

    def _compute_cost(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Look up the price table and compute USD cost."""
        key = f"{provider}/{model}"
        prices = TOKEN_COSTS.get(key) or TOKEN_COSTS.get("__default__", {"input": 0.0, "output": 0.0})
        cost = (input_tokens * prices["input"]) + (output_tokens * prices["output"])
        return round(cost, 8)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_async(self, record: UsageRecord) -> None:
        t = threading.Thread(target=self._append_to_file, args=(record,), daemon=True)
        t.start()

    def _append_to_file(self, record: UsageRecord) -> None:
        try:
            existing: list = []
            if _USAGE_FILE.exists():
                try:
                    existing = json.loads(_USAGE_FILE.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    existing = []
            existing.append(asdict(record))
            _USAGE_FILE.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not persist usage record: %s", exc)

    def _load_from_disk(self) -> None:
        if not _USAGE_FILE.exists():
            return
        try:
            data = json.loads(_USAGE_FILE.read_text(encoding="utf-8"))
            for item in data:
                try:
                    self._records.append(UsageRecord(**item))
                except (TypeError, KeyError):
                    pass
            logger.info("Loaded %d usage records from disk.", len(self._records))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load usage log: %s", exc)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

usage_tracker = UsageTracker()
