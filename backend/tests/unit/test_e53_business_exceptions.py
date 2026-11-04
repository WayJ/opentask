"""E53: business-hours exceptions pure helpers (TDD)."""
from __future__ import annotations

from datetime import datetime

import pytest

from opentask.services.sla.business_hours import (
    MAX_EXCEPTIONS,
    add_business_minutes,
    default_forced_open_windows,
    elapsed_business_minutes,
    normalize_business_hours,
    normalize_exceptions,
    resolve_day_segments,
)


def _utc(y, m, d, hh, mm=0) -> datetime:
    return datetime(y, m, d, hh, mm, 0)


def _mon_fri():
    return {
        **{d: [{"start": "09:00", "end": "18:00"}] for d in ("mon", "tue", "wed", "thu", "fri")},
        **{d: [] for d in ("sat", "sun")},
    }


def test_normalize_exceptions_rejects_bad_date_kind_dup_cap():
    with pytest.raises(ValueError):
        normalize_exceptions([{"date": "2026-13-01", "kind": "closed"}])
    with pytest.raises(ValueError):
        normalize_exceptions([{"date": "2026-11-05", "kind": "holiday"}])
    with pytest.raises(ValueError):
        normalize_exceptions(
            [
                {"date": "2026-11-05", "kind": "closed"},
                {"date": "2026-11-05", "kind": "forced_open"},
            ]
        )
    with pytest.raises(ValueError, match="366"):
        normalize_exceptions(
            [
                {"date": f"2027-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}", "kind": "closed"}
                for i in range(MAX_EXCEPTIONS + 1)
            ]
        )


def test_normalize_exceptions_ok_sorted_unique():
    out = normalize_exceptions(
        [
            {"date": "2026-11-06", "kind": "closed"},
            {
                "date": "2026-11-07",
                "kind": "forced_open",
                "windows": [{"start": "10:00", "end": "12:00"}],
            },
        ]
    )
    assert out == [
        {"date": "2026-11-06", "kind": "closed"},
        {
            "date": "2026-11-07",
            "kind": "forced_open",
            "windows": [{"start": "10:00", "end": "12:00"}],
        },
    ]


def test_default_forced_open_uses_monday_or_0918():
    assert default_forced_open_windows(_mon_fri()) == [{"start": "09:00", "end": "18:00"}]
    empty_mon = {**_mon_fri(), "mon": []}
    assert default_forced_open_windows(empty_mon) == [{"start": "09:00", "end": "18:00"}]
    custom = {**_mon_fri(), "mon": [{"start": "10:00", "end": "16:00"}]}
    assert default_forced_open_windows(custom) == [{"start": "10:00", "end": "16:00"}]


def test_resolve_closed_and_forced_open():
    day = datetime(2026, 11, 5, 12, 0)  # Thursday
    win = _mon_fri()
    assert resolve_day_segments(day, win, [{"date": "2026-11-05", "kind": "closed"}]) == []
    segs = resolve_day_segments(
        day,
        win,
        [
            {
                "date": "2026-11-05",
                "kind": "forced_open",
                "windows": [{"start": "10:00", "end": "12:00"}],
            }
        ],
    )
    assert segs == [{"start": "10:00", "end": "12:00"}]
    sat = datetime(2026, 11, 7, 12, 0)
    segs2 = resolve_day_segments(sat, win, [{"date": "2026-11-07", "kind": "forced_open"}])
    assert segs2 == [{"start": "09:00", "end": "18:00"}]
    # no exception → weekday
    assert resolve_day_segments(day, win, []) == [{"start": "09:00", "end": "18:00"}]


def test_add_skips_closed_day_across_holiday():
    # Thu 2026-11-05 17:00 Shanghai = UTC 09:00; Fri closed; +120 → Mon 10:00 CST = UTC 02:00
    start = _utc(2026, 11, 5, 9, 0)
    win = _mon_fri()
    ex = [{"date": "2026-11-06", "kind": "closed"}]
    deadline = add_business_minutes(start, 120, "Asia/Shanghai", win, exceptions=ex)
    assert deadline == _utc(2026, 11, 9, 2, 0)


def test_add_forced_open_on_empty_weekday():
    # Sat 2026-11-07 10:00 Shanghai = UTC 02:00; forced_open default 09–18; +60 → 11:00 = UTC 03:00
    start = _utc(2026, 11, 7, 2, 0)
    win = _mon_fri()
    ex = [{"date": "2026-11-07", "kind": "forced_open"}]
    deadline = add_business_minutes(start, 60, "Asia/Shanghai", win, exceptions=ex)
    assert deadline == _utc(2026, 11, 7, 3, 0)


def test_elapsed_skips_closed():
    win = _mon_fri()
    a = _utc(2026, 11, 5, 9, 0)  # Thu 17:00 CST
    b = _utc(2026, 11, 9, 2, 0)  # Mon 10:00 CST
    # Thu 17–18=60, Fri closed=0, weekend=0, Mon 09–10=60 → 120
    assert (
        elapsed_business_minutes(
            a, b, "Asia/Shanghai", win, exceptions=[{"date": "2026-11-06", "kind": "closed"}]
        )
        == 120
    )


def test_normalize_business_hours_includes_exceptions():
    bh = normalize_business_hours(
        {
            "enabled": True,
            "windows": _mon_fri(),
            "exceptions": [{"date": "2026-10-01", "kind": "closed"}],
        }
    )
    assert bh["exceptions"] == [{"date": "2026-10-01", "kind": "closed"}]
    assert normalize_business_hours(None)["exceptions"] == []
