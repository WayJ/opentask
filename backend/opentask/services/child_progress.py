"""E70: sub-issue childProgress aggregation helpers (direct children only)."""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

CHILD_PROGRESS_DONE_STATUSES = frozenset({"resolved", "closed", "rejected"})


def _norm_status(s: Any) -> str:
    if s is None:
        return ""
    if hasattr(s, "value"):
        return str(s.value)
    return str(s)


def compute_child_progress(statuses: Iterable[Any]) -> dict:
    """Aggregate direct-child statuses into childProgress payload.

    done = resolved|closed|rejected (Q1a / E39 CLOSED_STATUSES).
    percent = round(done/total*100) if total>0 else None (Q3a).
    """
    norms = [_norm_status(s) for s in statuses]
    by_status = dict(Counter(n for n in norms if n))
    total = len(norms)
    done = sum(by_status.get(s, 0) for s in CHILD_PROGRESS_DONE_STATUSES)
    open_count = total - done
    percent = round(done / total * 100) if total > 0 else None
    return {
        "total": total,
        "done": done,
        "open": open_count,
        "percent": percent,
        "byStatus": by_status,
    }
