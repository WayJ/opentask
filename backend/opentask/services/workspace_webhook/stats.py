"""E54: webhook delivery observability — pure stats helpers."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

STAT_WINDOWS: dict[str, timedelta] = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}
DEFAULT_WINDOW = "7d"
BULK_RETRY_CAP = 50


def parse_window(raw: Optional[str]) -> str:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return DEFAULT_WINDOW
    key = str(raw).strip()
    if key not in STAT_WINDOWS:
        raise ValueError("invalid_window")
    return key


def window_since(window: str, *, now: Optional[datetime] = None) -> datetime:
    key = parse_window(window)
    base = now or datetime.utcnow()
    return base - STAT_WINDOWS[key]


def success_rate(success: int, dead: int, pending_retry: int) -> Optional[float]:
    """Q2a: denominator = success + dead + pending_retry."""
    denom = int(success) + int(dead) + int(pending_retry)
    if denom <= 0:
        return None
    return int(success) / denom


def percentile_nearest_rank(sorted_vals: list[int], p: float) -> Optional[int]:
    if not sorted_vals:
        return None
    if p <= 0 or p > 1:
        raise ValueError("percentile p must be in (0, 1]")
    n = len(sorted_vals)
    # nearest-rank: index = ceil(p * n) - 1
    import math

    idx = max(0, min(n - 1, math.ceil(p * n) - 1))
    return int(sorted_vals[idx])


def _resolve_status(row: dict[str, Any]) -> str:
    status = row.get("status")
    if status:
        return str(status)
    if row.get("success"):
        return "success"
    return "pending_retry"


def aggregate_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    success = dead = pending_retry = 0
    latencies: list[int] = []
    for row in rows:
        st = _resolve_status(row)
        if st == "success" or st == "success_after_retry":
            success += 1
        elif st == "dead":
            dead += 1
        elif st == "pending_retry":
            pending_retry += 1
        else:
            # unknown → count as pending_retry (attempted, not settled)
            pending_retry += 1
        lat = row.get("latencyMs")
        if lat is None:
            lat = row.get("latency_ms")
        if lat is not None:
            try:
                latencies.append(int(lat))
            except (TypeError, ValueError):
                pass
    out: dict[str, Any] = {
        "success": success,
        "pending_retry": pending_retry,
        "dead": dead,
        "attempts": len(rows),
        "successRate": success_rate(success, dead, pending_retry),
    }
    if latencies:
        vals = sorted(latencies)
        out["latencyMs"] = {
            "p50": percentile_nearest_rank(vals, 0.50),
            "p95": percentile_nearest_rank(vals, 0.95),
        }
    return out
