"""E50/E53: workspace business-hours pure helpers (timezone + weekday windows + exceptions)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
EXCEPTION_KINDS = ("closed", "forced_open")
MAX_EXCEPTIONS = 366
_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_MAX_SEGMENTS = 2
_MAX_SCAN_DAYS = 370
_DEFAULT_FORCED_SEG = [{"start": "09:00", "end": "18:00"}]


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


def _validate_date(s: str) -> str:
    raw = str(s).strip()
    m = _DATE.match(raw)
    if not m:
        raise ValueError(f"非法日期: {s}")
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        datetime(y, mo, d)
    except ValueError as e:
        raise ValueError(f"非法日期: {s}") from e
    return f"{y:04d}-{mo:02d}-{d:02d}"


def _normalize_segment_list(segs_in: Any, *, label: str) -> list[dict[str, str]]:
    if segs_in is None:
        return []
    if not isinstance(segs_in, list):
        raise ValueError(f"{label} windows 必须是数组")
    if len(segs_in) > _MAX_SEGMENTS:
        raise ValueError(f"{label} 每日最多 {_MAX_SEGMENTS} 段")
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
            raise ValueError(f"{label} 时段倒置或空: {start_s}-{end_s}（要求 start < end）")
        parsed.append((start_m, end_m, f"{sh:02d}:{sm:02d}", f"{eh:02d}:{em:02d}"))
    parsed.sort(key=lambda x: x[0])
    merged: list[tuple[int, int, str, str]] = []
    for item in parsed:
        if not merged:
            merged.append(item)
            continue
        ps, pe, pss, pes = merged[-1]
        cs, ce, css, ces = item
        if cs <= pe:
            if ce > pe:
                merged[-1] = (ps, ce, pss, ces)
        else:
            merged.append(item)
    if len(merged) > _MAX_SEGMENTS:
        raise ValueError(f"{label} 每日最多 {_MAX_SEGMENTS} 段")
    return [{"start": s, "end": e} for _, _, s, e in merged]


def normalize_windows(windows: Optional[dict]) -> dict[str, list[dict[str, str]]]:
    raw = windows if isinstance(windows, dict) else {}
    out = _empty_windows()
    for key in WEEKDAY_KEYS:
        segs_in = raw.get(key) or raw.get(key.upper()) or []
        out[key] = _normalize_segment_list(segs_in, label=key)
    return out


def default_forced_open_windows(windows: Optional[dict]) -> list[dict[str, str]]:
    """Q2a: reuse Monday window if present; else 09:00–18:00 single segment."""
    win = normalize_windows(windows)
    mon = win.get("mon") or []
    if mon:
        return [{"start": s["start"], "end": s["end"]} for s in mon]
    return list(_DEFAULT_FORCED_SEG)


def normalize_exceptions(
    raw: Optional[list],
    *,
    windows_for_default: Optional[dict] = None,
) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("exceptions 必须是数组")
    if len(raw) > MAX_EXCEPTIONS:
        raise ValueError(f"exceptions 最多 {MAX_EXCEPTIONS} 条")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("exception 必须是对象")
        date_s = _validate_date(item.get("date", ""))
        kind = str(item.get("kind", "")).strip()
        if kind not in EXCEPTION_KINDS:
            raise ValueError(f"未知 exception kind: {kind}")
        if date_s in seen:
            raise ValueError(f"重复 exception date: {date_s}")
        seen.add(date_s)
        entry: dict[str, Any] = {"date": date_s, "kind": kind}
        if kind == "forced_open" and "windows" in item and item.get("windows") is not None:
            segs = _normalize_segment_list(item.get("windows"), label=date_s)
            entry["windows"] = segs
        elif kind == "closed" and item.get("windows"):
            # closed ignores windows; reject non-empty to keep API strict? design says windows optional
            # ignore silently for closed
            pass
        out.append(entry)
    out.sort(key=lambda x: x["date"])
    return out


def normalize_business_hours(raw: Optional[dict]) -> dict[str, Any]:
    if raw is None or not isinstance(raw, dict):
        return {"enabled": False, "windows": _empty_windows(), "exceptions": []}
    enabled = bool(raw.get("enabled", False))
    windows = normalize_windows(raw.get("windows"))
    exceptions = normalize_exceptions(raw.get("exceptions"), windows_for_default=windows)
    return {"enabled": enabled, "windows": windows, "exceptions": exceptions}


def resolve_day_segments(
    local_day: datetime,
    windows: dict,
    exceptions: Optional[list] = None,
) -> list[dict[str, str]]:
    win = normalize_windows(windows)
    ex_list = normalize_exceptions(exceptions, windows_for_default=win) if exceptions else []
    day_s = f"{local_day.year:04d}-{local_day.month:02d}-{local_day.day:02d}"
    for ex in ex_list:
        if ex["date"] != day_s:
            continue
        if ex["kind"] == "closed":
            return []
        # forced_open
        if ex.get("windows"):
            return list(ex["windows"])
        return default_forced_open_windows(win)
    return list(win.get(_day_key(local_day)) or [])


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
    exceptions: Optional[list] = None,
) -> datetime:
    """Add business minutes; return naive UTC deadline."""
    start = _as_utc_naive(start_utc)
    mins = int(minutes)
    if mins <= 0:
        return start
    tz = ZoneInfo(validate_timezone(tz_name) or "UTC")
    win = normalize_windows(windows)
    ex = normalize_exceptions(exceptions, windows_for_default=win) if exceptions else []
    cursor = _to_local(start, tz)
    remaining = mins
    for _ in range(_MAX_SCAN_DAYS * 4):
        if remaining <= 0:
            break
        day_start = cursor.replace(hour=0, minute=0, second=0, microsecond=0)
        segs = resolve_day_segments(day_start, win, ex)
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
        next_day = day_start + timedelta(days=1)
        if cursor < next_day:
            cursor = next_day
            advanced = True
        if not advanced:
            cursor = next_day
    return start + timedelta(minutes=mins)


def elapsed_business_minutes(
    a_utc: datetime,
    b_utc: datetime,
    tz_name: str,
    windows: dict,
    exceptions: Optional[list] = None,
) -> int:
    """Count business minutes in [a, b) (half-open via minute flooring)."""
    a = _as_utc_naive(a_utc)
    b = _as_utc_naive(b_utc)
    if b <= a:
        return 0
    tz = ZoneInfo(validate_timezone(tz_name) or "UTC")
    win = normalize_windows(windows)
    ex = normalize_exceptions(exceptions, windows_for_default=win) if exceptions else []
    cursor = _to_local(a, tz)
    end = _to_local(b, tz)
    total = 0
    for _ in range(_MAX_SCAN_DAYS * 4):
        if cursor >= end:
            break
        day_start = cursor.replace(hour=0, minute=0, second=0, microsecond=0)
        segs = resolve_day_segments(day_start, win, ex)
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


def normalize_policy_calendar(raw: Any) -> Optional[dict[str, Any]]:
    """E56 Q1a/Q4a: policy.calendar overlay. None/{} = full inherit WS."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("calendar 必须是对象或 null")
    if not raw:
        return None
    out: dict[str, Any] = {}
    if "timezone" in raw and raw.get("timezone") is not None:
        tz = validate_timezone(raw.get("timezone"))
        if tz is None:
            raise ValueError("非法 IANA timezone")
        out["timezone"] = tz
    if "windows" in raw and raw.get("windows") is not None:
        out["windows"] = normalize_windows(raw.get("windows"))
    if "exceptions" in raw and raw.get("exceptions") is not None:
        win_for_default = out.get("windows")
        out["exceptions"] = normalize_exceptions(
            raw.get("exceptions"), windows_for_default=win_for_default
        )
    return out if out else None


def resolve_effective_calendar(
    ws: Any,
    policy: Any = None,
) -> Optional[dict[str, Any]]:
    """Merge WS + optional policy.calendar → {timezone,windows,exceptions} or None (wall-clock).

    Q2a: when WS business_hours.enabled=false (or no usable tz), always wall-clock;
    policy overlay cannot force-open business minutes.
    """
    if ws is None:
        return None
    bh_raw = getattr(ws, "business_hours", None)
    tz_raw = getattr(ws, "timezone", None)
    if not is_business_hours_enabled(tz_raw, bh_raw):
        return None
    bh = bh_raw if isinstance(bh_raw, dict) else {}
    cal_raw = getattr(policy, "calendar", None) if policy is not None else None
    cal = cal_raw if isinstance(cal_raw, dict) else {}
    if "timezone" in cal and cal.get("timezone") is not None:
        tz = validate_timezone(cal.get("timezone")) or str(tz_raw)
    else:
        tz = str(tz_raw)
    if "windows" in cal and cal.get("windows") is not None:
        windows = normalize_windows(cal.get("windows"))
    else:
        windows = normalize_windows(bh.get("windows"))
    if "exceptions" in cal and cal.get("exceptions") is not None:
        exceptions = normalize_exceptions(
            cal.get("exceptions"), windows_for_default=windows
        )
    else:
        exceptions = normalize_exceptions(
            bh.get("exceptions") or [], windows_for_default=windows
        )
    return {"timezone": tz, "windows": windows, "exceptions": exceptions}
