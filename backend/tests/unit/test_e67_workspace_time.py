"""E67: workspace local calendar day helpers."""
from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from opentask.services.workspace_time import local_today, resolve_workspace_tz


def test_resolve_none_empty_invalid_to_utc():
    assert resolve_workspace_tz(None) == ZoneInfo("UTC")
    assert resolve_workspace_tz(SimpleNamespace(timezone=None)) == ZoneInfo("UTC")
    assert resolve_workspace_tz(SimpleNamespace(timezone="")) == ZoneInfo("UTC")
    assert resolve_workspace_tz(SimpleNamespace(timezone="Not/A_Zone")) == ZoneInfo("UTC")


def test_resolve_asia_shanghai():
    assert resolve_workspace_tz(SimpleNamespace(timezone="Asia/Shanghai")) == ZoneInfo(
        "Asia/Shanghai"
    )


def test_local_today_crosses_utc_midnight_shanghai():
    # UTC 2026-11-05 16:30 → Shanghai 2026-11-06 00:30
    now = datetime(2026, 11, 5, 16, 30, 0, tzinfo=timezone.utc)
    ws = SimpleNamespace(timezone="Asia/Shanghai")
    assert local_today(ws, now_utc=now) == date(2026, 11, 6)


def test_local_today_none_tz_stays_utc_day():
    now = datetime(2026, 11, 5, 16, 30, 0)  # naive = UTC
    ws = SimpleNamespace(timezone=None)
    assert local_today(ws, now_utc=now) == date(2026, 11, 5)


def test_resolve_string_tz():
    assert resolve_workspace_tz("UTC") == ZoneInfo("UTC")
    assert resolve_workspace_tz("Europe/London") == ZoneInfo("Europe/London")
