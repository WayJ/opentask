"""E50: workspace business-hours pure helpers (timezone + weekday windows)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_MAX_SEGMENTS = 2
_MAX_SCAN_DAYS = 370


def _empty_windows() -> dict[str, list[dict[str, str]]]:
    return {k: [] for k in WEEKDAY_KEYS}


WEEKDAY_PRESET_09_18: dict[str, list[dict[str, str]]] = {
    **_empty_windows(),
    **{d: [{"start": "09:00", "end": "18:00"}] for d in ("mon", "tue", "wed", "thu", "fri")},
}


def validate_timezone(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    s = str(name).strip()
    if not s:
        return None
    try:
        ZoneInfo(s)
    except ZoneInfoNotFoundError as e:
        raise ValueError(f"非法 IANA timezone: {s}") from e
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"非法 IANA timezone: {s}") from e
    return s


def _parse_hhmm(s: str) -> tuple[int, int]:
    m = _HHMM.match(str(s).strip())
    if not m:
        raise ValueError(f"非法 HH:MM: {s}")
    return int(m.group(1)), int(m.group(2))


def _minutes_of_day(hh: int, mm: int) -> int:
    return hh * 60 + mm


def normalize_windows(windows: Optional[dict]) -> dict[str, list[dict[str, str]]]:
    raw = windows if isinstance(windows, dict) else {}
    out = _empty_windows()
    for key in WEEKDAY_KEYS:
        segs_in = raw.get(key) or raw.get(key.upper()) or []
        if not isinstance(segs_in, list):
            raise ValueError(f"{key} windows 必须是数组")
        if len(segs_in) > _MAX_SEGMENTS:
            raise ValueError(f"{key} 每日最多 {_MAX_SEGMENTS} 段")
        parsed: list[tuple[int, int, str, str]] = []
        for seg in segs_in:
            if not isinstance(seg, dict):
                raise ValueError("window 段必须是对象")
            start_s = str(seg.get("start", "")).strip()
            end_s = str(seg.get("end", "")).strip()
            sh, sm = _parse_hhmm(start_s)
            eh, em = _parse_hhmm(end_s)
            start_m = _minutes_of_day(sh, sm)
            end_m = _minutes_of_day(eh, em)
            if start_m >= end_m:
                raise ValueError(f"{key} 时段倒置或空: {start_s}-{end_s}（要求 start < end）")
            parsed.append((start_m, end_m, f"{sh:02d}:{sm:02d}", f"{eh:02d}:{em:02d}"))
        parsed.sort(key=lambda x: x[0])
        merged: list[tuple[int, int, str, str]] = []
        for item in parsed:
            if not merged:
                merged.append(item)
                continue
            ps, pe, pss, pes = merged[-1]
            cs, ce, css, ces = item
            if cs <= pe:  # overlap or touch → merge
                if ce > pe:
                    merged[-1] = (ps, ce, pss, ces)
                # else fully contained
            else:
                merged.append(item)
        if len(merged) > _MAX_SEGMENTS:
            raise ValueError(f"{key} 每日最多 {_MAX_SEGMENTS} 段")
        out[key] = [{"start": s, "end": e} for _, _, s, e in merged]
    return out


def normalize_business_hours(raw: Optional[dict]) -> dict[str, Any]:
    if raw is None or not isinstance(raw, dict):
        return {"enabled": False, "windows": _empty_windows()}
    enabled = bool(raw.get("enabled", False))
    windows = normalize_windows(raw.get("windows"))
    return {"enabled": enabled, "windows": windows}


def _as_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _to_local(dt_utc_naive: datetime, tz: ZoneInfo) -> datetime:
    return dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(tz)


def _to_utc_naive(local_aware: datetime) -> datetime:
    return local_aware.astimezone(timezone.utc).replace(tzinfo=None)


def _day_key(local: datetime) -> str:
    return WEEKDAY_KEYS[local.weekday()]


def _seg_bounds_local(day: datetime, seg: dict[str, str]) -> tuple[datetime, datetime]:
    sh, sm = _parse_hhmm(seg["start"])
    eh, em = _parse_hhmm(seg["end"])
    start = day.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end = day.replace(hour=eh, minute=em, second=0, microsecond=0)
    return start, end


def add_business_minutes(
    start_utc: datetime,
    minutes: int,
    tz_name: str,
    windows: dict,
) -> datetime:
    """Add business minutes; return naive UTC deadline."""
    start = _as_utc_naive(start_utc)
    mins = int(minutes)
    if mins <= 0:
        return start
    tz = ZoneInfo(validate_timezone(tz_name) or "UTC")
    win = normalize_windows(windows)
    cursor = _to_local(start, tz)
    remaining = mins
    for _ in range(_MAX_SCAN_DAYS * 4):
        if remaining <= 0:
            break
        day_start = cursor.replace(hour=0, minute=0, second=0, microsecond=0)
        segs = win.get(_day_key(cursor)) or []
        advanced = False
        for seg in segs:
            seg_start, seg_end = _seg_bounds_local(day_start, seg)
            if cursor >= seg_end:
                continue
            effective = cursor if cursor > seg_start else seg_start
            if effective >= seg_end:
                continue
            available = int((seg_end - effective).total_seconds() // 60)
            if available <= 0:
                continue
            if remaining <= available:
                result_local = effective + timedelta(minutes=remaining)
                return _to_utc_naive(result_local)
            remaining -= available
            cursor = seg_end
            advanced = True
        # move to next local midnight
        next_day = day_start + timedelta(days=1)
        if cursor < next_day:
            cursor = next_day
            advanced = True
        if not advanced:
            cursor = next_day
    # Fallback: wall clock if calendar empty for too long
    return start + timedelta(minutes=mins)


def elapsed_business_minutes(
    a_utc: datetime,
    b_utc: datetime,
    tz_name: str,
    windows: dict,
) -> int:
    """Count business minutes in [a, b) (half-open via minute flooring)."""
    a = _as_utc_naive(a_utc)
    b = _as_utc_naive(b_utc)
    if b <= a:
        return 0
    tz = ZoneInfo(validate_timezone(tz_name) or "UTC")
    win = normalize_windows(windows)
    cursor = _to_local(a, tz)
    end = _to_local(b, tz)
    total = 0
    for _ in range(_MAX_SCAN_DAYS * 4):
        if cursor >= end:
            break
        day_start = cursor.replace(hour=0, minute=0, second=0, microsecond=0)
        segs = win.get(_day_key(cursor)) or []
        progressed = False
        for seg in segs:
            seg_start, seg_end = _seg_bounds_local(day_start, seg)
            if cursor >= seg_end:
                continue
            effective_start = cursor if cursor > seg_start else seg_start
            effective_end = end if end < seg_end else seg_end
            if effective_start >= effective_end:
                continue
            total += int((effective_end - effective_start).total_seconds() // 60)
            cursor = effective_end
            progressed = True
            if cursor >= end:
                break
        if cursor >= end:
            break
        next_day = day_start + timedelta(days=1)
        if cursor < next_day:
            cursor = next_day
            progressed = True
        if not progressed:
            cursor = next_day
    return max(0, total)


def is_business_hours_enabled(ws_timezone: Optional[str], business_hours: Optional[dict]) -> bool:
    bh = business_hours if isinstance(business_hours, dict) else {}
    if not bool(bh.get("enabled")):
        return False
    try:
        return validate_timezone(ws_timezone) is not None
    except ValueError:
        return False
