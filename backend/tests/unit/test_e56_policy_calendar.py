"""E56: policy calendar normalize + effective merge (TDD)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from opentask.services.sla.business_hours import (
    WEEKDAY_PRESET_09_18,
    normalize_policy_calendar,
    resolve_effective_calendar,
)


def _ws(**kw):
    base = dict(
        timezone="Asia/Shanghai",
        business_hours={
            "enabled": True,
            "windows": WEEKDAY_PRESET_09_18,
            "exceptions": [{"date": "2026-10-01", "kind": "closed"}],
        },
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _pol(calendar=None):
    return SimpleNamespace(calendar=calendar)


def test_normalize_none_and_empty():
    assert normalize_policy_calendar(None) is None
    assert normalize_policy_calendar({}) is None


def test_normalize_partial_fields_and_rejects():
    out = normalize_policy_calendar({"timezone": "America/New_York"})
    assert out == {"timezone": "America/New_York"}
    out2 = normalize_policy_calendar(
        {
            "windows": WEEKDAY_PRESET_09_18,
            "exceptions": [{"date": "2026-11-05", "kind": "closed"}],
        }
    )
    assert "windows" in out2 and out2["exceptions"][0]["kind"] == "closed"
    with pytest.raises(ValueError):
        normalize_policy_calendar({"timezone": "Not/AZone"})
    with pytest.raises(ValueError):
        normalize_policy_calendar({"exceptions": [{"date": "2026-11-05", "kind": "holiday"}]})
    with pytest.raises(ValueError):
        normalize_policy_calendar(
            {
                "exceptions": [
                    {"date": "2026-11-05", "kind": "closed"},
                    {"date": "2026-11-05", "kind": "forced_open"},
                ]
            }
        )
    with pytest.raises(ValueError):
        normalize_policy_calendar("nope")


def test_resolve_inherits_and_overrides():
    ws = _ws()
    assert resolve_effective_calendar(ws, _pol(None))["timezone"] == "Asia/Shanghai"
    assert resolve_effective_calendar(ws, _pol(None))["exceptions"][0]["date"] == "2026-10-01"
    eff = resolve_effective_calendar(ws, _pol({"timezone": "UTC"}))
    assert eff["timezone"] == "UTC"
    assert eff["exceptions"][0]["date"] == "2026-10-01"
    eff2 = resolve_effective_calendar(
        ws,
        _pol({"exceptions": [{"date": "2026-11-07", "kind": "forced_open"}]}),
    )
    assert eff2["timezone"] == "Asia/Shanghai"
    assert eff2["exceptions"] == [{"date": "2026-11-07", "kind": "forced_open"}]


def test_resolve_q2a_ws_disabled_wall_clock():
    ws = _ws(
        business_hours={
            "enabled": False,
            "windows": WEEKDAY_PRESET_09_18,
            "exceptions": [],
        }
    )
    assert (
        resolve_effective_calendar(
            ws, _pol({"timezone": "UTC", "windows": WEEKDAY_PRESET_09_18})
        )
        is None
    )
    assert resolve_effective_calendar(None, _pol({"timezone": "UTC"})) is None
