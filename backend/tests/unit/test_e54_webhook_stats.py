"""E54: webhook delivery stats pure helpers (TDD)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from opentask.services.workspace_webhook.stats import (
    BULK_RETRY_CAP,
    DEFAULT_WINDOW,
    STAT_WINDOWS,
    aggregate_totals,
    parse_window,
    percentile_nearest_rank,
    success_rate,
    window_since,
)


def test_parse_window_default_and_whitelist():
    assert parse_window(None) == DEFAULT_WINDOW == "7d"
    assert parse_window("") == "7d"
    assert parse_window("24h") == "24h"
    assert parse_window("30d") == "30d"
    with pytest.raises(ValueError, match="invalid_window"):
        parse_window("1h")
    assert set(STAT_WINDOWS) == {"24h", "7d", "30d"}
    assert BULK_RETRY_CAP == 50


def test_window_since_offsets():
    now = datetime(2026, 11, 5, 12, 0, 0)
    assert window_since("24h", now=now) == now - timedelta(hours=24)
    assert window_since("7d", now=now) == now - timedelta(days=7)
    assert window_since("30d", now=now) == now - timedelta(days=30)


def test_success_rate_q2a_includes_pending():
    assert success_rate(8, 1, 1) == 0.8
    assert success_rate(0, 0, 0) is None
    assert success_rate(0, 2, 0) == 0.0


def test_percentile_and_aggregate():
    assert percentile_nearest_rank([], 0.5) is None
    assert percentile_nearest_rank([10, 20, 30, 40], 0.5) == 20
    rows = [
        {"status": "success", "latencyMs": 100},
        {"status": "success", "latencyMs": 200},
        {"status": "dead", "latencyMs": 50},
        {"status": "pending_retry", "latencyMs": None},
        {"status": None, "success": True, "latencyMs": 150},
    ]
    tot = aggregate_totals(rows)
    assert tot["success"] == 3
    assert tot["dead"] == 1
    assert tot["pending_retry"] == 1
    assert tot["attempts"] == 5
    assert tot["successRate"] == 0.6
    assert tot["latencyMs"]["p50"] is not None
    assert tot["latencyMs"]["p95"] is not None
    bare = aggregate_totals([{"status": "success"}, {"status": "dead"}])
    assert "latencyMs" not in bare
