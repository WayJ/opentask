"""E73: issue planned start_date helpers (independent of started_at)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Union

from fastapi import HTTPException

DateLike = Union[datetime, date, None]


def _as_date(value: DateLike) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise TypeError(f"unsupported date-like: {type(value)!r}")


def validate_start_due(*, start_date: DateLike, due_date: DateLike) -> None:
    """Q1a: when both set, require start.date <= due.date else 400."""
    s = _as_date(start_date)
    d = _as_date(due_date)
    if s is None or d is None:
        return
    if s > d:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "start_after_due",
                "message": "start_date must be on or before due_date",
            },
        )
