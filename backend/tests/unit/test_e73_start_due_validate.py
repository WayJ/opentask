"""E73: start_date vs due_date calendar validation."""
from __future__ import annotations

from datetime import date, datetime

import pytest
from fastapi import HTTPException

from opentask.services.issue_dates import validate_start_due


def test_both_none_ok():
    validate_start_due(start_date=None, due_date=None)


def test_only_start_ok():
    validate_start_due(start_date=datetime(2026, 11, 10), due_date=None)


def test_only_due_ok():
    validate_start_due(start_date=None, due_date=datetime(2026, 11, 10))


def test_same_day_ok():
    validate_start_due(
        start_date=datetime(2026, 11, 10, 8, 0),
        due_date=datetime(2026, 11, 10, 18, 0),
    )


def test_start_before_due_ok():
    validate_start_due(
        start_date=date(2026, 11, 9),
        due_date=date(2026, 11, 10),
    )


def test_start_after_due_400():
    with pytest.raises(HTTPException) as ei:
        validate_start_due(
            start_date=datetime(2026, 11, 10),
            due_date=datetime(2026, 11, 9),
        )
    assert ei.value.status_code == 400
    assert ei.value.detail["code"] == "start_after_due"
