"""E35 TDD：UTC schedule helpers（advance / expand / monthday clamp）."""
from __future__ import annotations

from datetime import datetime

from opentask.services.issue_recurrence.service import (
    advance_once,
    advance_until_future,
    expand_title,
    snap_monthday,
    snap_weekday,
)


def test_expand_title_placeholders():
    when = datetime(2026, 11, 4, 15, 30, 0)
    assert expand_title("A {date}", when) == "A 2026-11-04"
    assert expand_title("B {yyyy-mm-dd}", when) == "B 2026-11-04"


def test_advance_daily_until_future_skips_gap():
    start = datetime(2026, 11, 1, 9, 0, 0)
    now = datetime(2026, 11, 4, 10, 0, 0)
    nxt = advance_until_future(
        start, now=now, interval="daily", weekday=None, monthday=None
    )
    assert nxt > now
    assert nxt == datetime(2026, 11, 5, 9, 0, 0)


def test_advance_weekly_preserves_weekday():
    # Thursday 2026-11-05; weekday=0 (Mon) → next Monday after +7 snap
    start = datetime(2026, 11, 5, 8, 0, 0)
    once = advance_once(start, "weekly", weekday=0, monthday=None)
    assert once.weekday() == 0


def test_monthly_monthday_clamps_overflow():
    jan31 = datetime(2026, 1, 31, 12, 0, 0)
    feb = advance_once(jan31, "monthly", weekday=None, monthday=31)
    assert feb.month == 2
    assert feb.day == 28  # 2026 not leap


def test_snap_helpers():
    assert snap_weekday(datetime(2026, 11, 4, 0, 0, 0), 0).weekday() == 0  # Wed→Mon next
    assert snap_monthday(datetime(2026, 2, 1, 0, 0, 0), 31).day == 28
