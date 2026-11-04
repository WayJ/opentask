"""E57: webhook dead-letter alert settings normalize / merge / mute / bucket."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

WINDOW_HOURS_MIN = 1
WINDOW_HOURS_MAX = 168  # 7d
DEFAULT_WINDOW_HOURS = 24
DEFAULT_DEAD_THRESHOLD = 10

DEFAULT_ALERT_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "windowHours": DEFAULT_WINDOW_HOURS,
    "deadThreshold": DEFAULT_DEAD_THRESHOLD,
    "consecutiveDeadThreshold": None,
    "autoDisable": False,
    "muteUntil": None,
}

_KNOWN_KEYS = frozenset(DEFAULT_ALERT_SETTINGS.keys())


def _parse_mute_until(raw: Any) -> Optional[str]:
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        raise ValueError("muteUntil must be ISO datetime string or null")
    s = raw.strip()
    if not s:
        return None
    try:
        # accept trailing Z
        datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("muteUntil must be ISO datetime") from exc
    return s


def _coerce_bool(v: Any, *, field: str) -> bool:
    if isinstance(v, bool):
        return v
    raise ValueError(f"{field} must be bool")


def _coerce_int(v: Any, *, field: str, min_v: int, max_v: Optional[int] = None) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        # reject bool (subclass of int) and non-int
        try:
            if isinstance(v, bool):
                raise ValueError
            if isinstance(v, float) and v == int(v):
                v = int(v)
            elif isinstance(v, str) and v.strip().lstrip("-").isdigit():
                v = int(v.strip())
            else:
                raise ValueError
        except ValueError as exc:
            raise ValueError(f"{field} must be int") from exc
    if v < min_v:
        raise ValueError(f"{field} must be >= {min_v}")
    if max_v is not None and v > max_v:
        raise ValueError(f"{field} must be <= {max_v}")
    return int(v)


def normalize_alert_settings(
    raw: Any, *, partial: bool = False
) -> Optional[dict[str, Any]]:
    """Normalize alert settings.

    partial=True (hook overlay): None/{} → None (inherit all); only present keys.
    partial=False (WS full): None/non-dict → defaults; always full shape.
    """
    if partial:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise ValueError("alert_settings must be object or null")
        if not raw:
            return None
        out: dict[str, Any] = {}
        for k, v in raw.items():
            if k not in _KNOWN_KEYS:
                raise ValueError(f"unknown alert setting: {k}")
            if k == "enabled":
                out[k] = _coerce_bool(v, field=k)
            elif k == "windowHours":
                out[k] = _coerce_int(
                    v, field=k, min_v=WINDOW_HOURS_MIN, max_v=WINDOW_HOURS_MAX
                )
            elif k == "deadThreshold":
                out[k] = _coerce_int(v, field=k, min_v=1)
            elif k == "consecutiveDeadThreshold":
                if v is None:
                    out[k] = None
                else:
                    out[k] = _coerce_int(v, field=k, min_v=1)
            elif k == "autoDisable":
                out[k] = _coerce_bool(v, field=k)
            elif k == "muteUntil":
                out[k] = _parse_mute_until(v)
        return out

    if raw is None:
        return dict(DEFAULT_ALERT_SETTINGS)
    if not isinstance(raw, dict):
        raise ValueError("alert_settings must be object or null")
    # start from defaults, overlay known keys via partial validation path
    base = dict(DEFAULT_ALERT_SETTINGS)
    if raw:
        part = normalize_alert_settings(raw, partial=True) or {}
        base.update(part)
    return base


def merge_alert_settings(
    ws_raw: Any, hook_raw: Any = None
) -> dict[str, Any]:
    """WS full settings + optional hook field overlay → effective settings."""
    base = normalize_alert_settings(ws_raw, partial=False) or dict(
        DEFAULT_ALERT_SETTINGS
    )
    overlay = normalize_alert_settings(hook_raw, partial=True)
    if overlay:
        base = {**base, **overlay}
    return base


def _as_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_muted(settings: dict[str, Any], *, now: Optional[datetime] = None) -> bool:
    mute = settings.get("muteUntil") if isinstance(settings, dict) else None
    if not mute:
        return False
    try:
        until = datetime.fromisoformat(str(mute).replace("Z", "+00:00"))
    except ValueError:
        return False
    n = now or datetime.utcnow()
    # compare naive as UTC wall
    if until.tzinfo is not None:
        until_naive = until.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        until_naive = until
    n_naive = n.replace(tzinfo=None) if n.tzinfo else n
    return n_naive < until_naive


def bucket_for(window_hours: int, *, now: Optional[datetime] = None) -> str:
    hours = max(WINDOW_HOURS_MIN, int(window_hours or DEFAULT_WINDOW_HOURS))
    n = now or datetime.utcnow()
    if n.tzinfo is not None:
        n = n.astimezone(timezone.utc).replace(tzinfo=None)
    epoch = int((n - datetime(1970, 1, 1)).total_seconds())
    step = hours * 3600
    return str(epoch // step)


def count_consecutive_dead(statuses_newest_first: list[str]) -> int:
    n = 0
    for st in statuses_newest_first:
        if st == "dead":
            n += 1
            continue
        if st in ("success", "success_after_retry"):
            break
        # pending_retry / other → break consecutive dead chain
        break
    return n


__all__ = [
    "DEFAULT_ALERT_SETTINGS",
    "DEFAULT_DEAD_THRESHOLD",
    "DEFAULT_WINDOW_HOURS",
    "WINDOW_HOURS_MAX",
    "WINDOW_HOURS_MIN",
    "bucket_for",
    "count_consecutive_dead",
    "is_muted",
    "merge_alert_settings",
    "normalize_alert_settings",
]
