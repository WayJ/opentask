"""E57: alert settings normalize/merge/mute/bucket (TDD)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from opentask.services.workspace_webhook.alert_settings import (
    DEFAULT_ALERT_SETTINGS,
    WINDOW_HOURS_MAX,
    WINDOW_HOURS_MIN,
    bucket_for,
    count_consecutive_dead,
    is_muted,
    merge_alert_settings,
    normalize_alert_settings,
)


def test_normalize_defaults_and_rejects():
    out = normalize_alert_settings(None)
    assert out["enabled"] is False
    assert out["windowHours"] == 24
    assert out["deadThreshold"] == 10
    assert out["consecutiveDeadThreshold"] is None
    assert out["autoDisable"] is False
    assert out["muteUntil"] is None
    assert out == {**DEFAULT_ALERT_SETTINGS}
    with pytest.raises(ValueError):
        normalize_alert_settings({"windowHours": 0})
    with pytest.raises(ValueError):
        normalize_alert_settings({"windowHours": WINDOW_HOURS_MAX + 1})
    with pytest.raises(ValueError):
        normalize_alert_settings({"deadThreshold": 0})
    with pytest.raises(ValueError):
        normalize_alert_settings({"consecutiveDeadThreshold": 0})
    with pytest.raises(ValueError):
        normalize_alert_settings({"muteUntil": "not-iso"})
    with pytest.raises(ValueError):
        normalize_alert_settings("nope")


def test_partial_overlay_and_merge():
    assert normalize_alert_settings(None, partial=True) is None
    assert normalize_alert_settings({}, partial=True) is None
    part = normalize_alert_settings(
        {"deadThreshold": 3, "enabled": True}, partial=True
    )
    assert part == {"deadThreshold": 3, "enabled": True}
    merged = merge_alert_settings(
        {"enabled": True, "windowHours": 24, "deadThreshold": 10},
        {"deadThreshold": 3},
    )
    assert merged["enabled"] is True
    assert merged["deadThreshold"] == 3
    assert merged["windowHours"] == 24
    assert merged["autoDisable"] is False


def test_mute_bucket_consecutive():
    now = datetime(2026, 11, 5, 12, 0, 0)
    assert (
        is_muted({"muteUntil": (now + timedelta(hours=1)).isoformat()}, now=now)
        is True
    )
    assert (
        is_muted({"muteUntil": (now - timedelta(hours=1)).isoformat()}, now=now)
        is False
    )
    assert is_muted({"muteUntil": None}, now=now) is False
    b1 = bucket_for(24, now=now)
    b2 = bucket_for(24, now=now + timedelta(hours=25))
    assert b1 != b2
    assert b1 == bucket_for(24, now=now + timedelta(hours=1))
    assert count_consecutive_dead(["dead", "dead", "success", "dead"]) == 2
    assert count_consecutive_dead(["success"]) == 0
    assert count_consecutive_dead(["dead", "dead"]) == 2
    assert WINDOW_HOURS_MIN == 1
    assert DEFAULT_ALERT_SETTINGS["enabled"] is False
