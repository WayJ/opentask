"""E50: pure business-minutes helpers (TDD)."""
from __future__ import annotations

from datetime import datetime

import pytest

from opentask.services.sla.business_hours import (
    WEEKDAY_KEYS,
    WEEKDAY_PRESET_09_18,
    add_business_minutes,
    elapsed_business_minutes,
    normalize_business_hours,
    normalize_windows,
    validate_timezone,
)


def _utc(y, m, d, hh, mm=0) -> datetime:
    return datetime(y, m, d, hh, mm, 0)


def test_weekday_keys_mon_sun():
    assert WEEKDAY_KEYS == ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def test_validate_timezone_accepts_iana_and_none():
    assert validate_timezone(None) is None
    assert validate_timezone("") is None
    assert validate_timezone("Asia/Shanghai") == "Asia/Shanghai"
    with pytest.raises(ValueError):
        validate_timezone("Not/A_Zone")


def test_normalize_windows_rejects_invert_and_too_many():
    with pytest.raises(ValueError, match="invert|start"):
        normalize_windows({"mon": [{"start": "18:00", "end": "09:00"}]})
    with pytest.raises(ValueError, match="2"):
        normalize_windows(
            {
                "mon": [
                    {"start": "09:00", "end": "10:00"},
                    {"start": "11:00", "end": "12:00"},
                    {"start": "13:00", "end": "14:00"},
                ]
            }
        )


def test_normalize_windows_merges_overlap():
    out = normalize_windows(
        {"mon": [{"start": "09:00", "end": "12:00"}, {"start": "11:00", "end": "14:00"}]}
    )
    assert out["mon"] == [{"start": "09:00", "end": "14:00"}]


def test_add_same_day_window():
    # 2026-11-02 is Monday. Shanghai 10:00 = UTC 02:00
    start = _utc(2026, 11, 2, 2, 0)
    windows = {"mon": [{"start": "09:00", "end": "18:00"}]}
    deadline = add_business_minutes(start, 60, "Asia/Shanghai", windows)
    assert deadline == _utc(2026, 11, 2, 3, 0)  # 11:00 Shanghai


def test_add_cross_lunch():
    # Mon 11:30 Shanghai = UTC 03:30; +60 across 12–13 lunch → 14:30 = UTC 06:30
    start = _utc(2026, 11, 2, 3, 30)
    windows = {
        "mon": [
            {"start": "09:00", "end": "12:00"},
            {"start": "13:00", "end": "18:00"},
        ]
    }
    deadline = add_business_minutes(start, 60, "Asia/Shanghai", windows)
    assert deadline == _utc(2026, 11, 2, 5, 30)  # 13:30 Shanghai


def test_add_cross_weekend():
    # Fri 2026-11-06 17:00 Shanghai = UTC 09:00; +120 with Mon–Fri 09–18
    # remaining after Fri: 60 → next Mon 09:00 + 60 = Mon 10:00 Shanghai = UTC 02:00
    start = _utc(2026, 11, 6, 9, 0)
    windows = {d: [{"start": "09:00", "end": "18:00"}] for d in ("mon", "tue", "wed", "thu", "fri")}
    deadline = add_business_minutes(start, 120, "Asia/Shanghai", windows)
    assert deadline == _utc(2026, 11, 9, 2, 0)  # Mon 10:00 CST


def test_elapsed_within_and_across_gap():
    windows = {
        "mon": [
            {"start": "09:00", "end": "12:00"},
            {"start": "13:00", "end": "18:00"},
        ]
    }
    a = _utc(2026, 11, 2, 3, 0)  # 11:00
    b = _utc(2026, 11, 2, 6, 0)  # 14:00
    # 11–12 = 60, lunch skip, 13–14 = 60 → 120
    assert elapsed_business_minutes(a, b, "Asia/Shanghai", windows) == 120


def test_elapsed_empty_day_zero():
    windows = {"sat": [], "sun": []}
    a = _utc(2026, 11, 7, 1, 0)  # Sat
    b = _utc(2026, 11, 8, 10, 0)  # Sun
    assert elapsed_business_minutes(a, b, "Asia/Shanghai", windows) == 0


def test_normalize_business_hours_defaults_and_preset():
    bh = normalize_business_hours(None)
    assert bh == {"enabled": False, "windows": {k: [] for k in WEEKDAY_KEYS}, "exceptions": []}
    assert WEEKDAY_PRESET_09_18["mon"] == [{"start": "09:00", "end": "18:00"}]
    assert WEEKDAY_PRESET_09_18["sat"] == []
