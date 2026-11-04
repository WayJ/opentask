"""E58: static holiday packs loader + merge (pack wins)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from opentask.data.holiday_packs import PACKS_ROOT as _DEFAULT_PACKS_ROOT

PACKS_ROOT = _DEFAULT_PACKS_ROOT
from opentask.services.sla.business_hours import (
    EXCEPTION_KINDS,
    MAX_EXCEPTIONS,
    normalize_exceptions,
)

_REGION_RE = re.compile(r"^[A-Z]{2}$")


def _pack_path(region: str, year: int, *, root: Optional[Path] = None) -> Path:
    base = root or PACKS_ROOT
    return base / region.upper() / f"{int(year)}.json"


def _validate_pack_dict(raw: Any, *, expect_region: str, expect_year: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("假日包必须是对象")
    region = str(raw.get("region", "")).strip().upper()
    if region != expect_region.upper():
        raise ValueError(f"假日包 region 不匹配: {region} != {expect_region}")
    try:
        year = int(raw.get("year"))
    except (TypeError, ValueError) as e:
        raise ValueError("假日包 year 非法") from e
    if year != int(expect_year):
        raise ValueError(f"假日包 year 不匹配: {year} != {expect_year}")
    name = str(raw.get("name") or "").strip()
    source_note = str(raw.get("sourceNote") or "").strip()
    holidays_in = raw.get("holidays")
    if not isinstance(holidays_in, list):
        raise ValueError("holidays 必须是数组")
    holidays: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in holidays_in:
        if not isinstance(item, dict):
            raise ValueError("holiday 必须是对象")
        date_s = str(item.get("date", "")).strip()
        kind = str(item.get("kind", "")).strip()
        if kind not in EXCEPTION_KINDS:
            raise ValueError(f"未知 holiday kind: {kind}")
        # reuse normalize via a single-item list for date validation
        normalized = normalize_exceptions([{"date": date_s, "kind": kind, **(
            {"windows": item["windows"]} if item.get("windows") is not None else {}
        )}])
        entry = dict(normalized[0])
        if date_s in seen:
            raise ValueError(f"重复 holiday date: {date_s}")
        seen.add(entry["date"])
        label = item.get("label")
        if label is not None and str(label).strip():
            entry["label"] = str(label).strip()
        holidays.append(entry)
    holidays.sort(key=lambda h: h["date"])
    return {
        "region": region,
        "year": year,
        "name": name or f"{region} {year}",
        "sourceNote": source_note,
        "holidays": holidays,
    }


def load_pack(region: str, year: int, *, root: Optional[Path] = None) -> dict[str, Any]:
    region_s = str(region or "").strip().upper()
    if not _REGION_RE.match(region_s):
        raise FileNotFoundError(f"假日包不存在: {region}/{year}")
    path = _pack_path(region_s, int(year), root=root)
    if not path.is_file():
        raise FileNotFoundError(f"假日包不存在: {region_s}/{year}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"假日包 JSON 无效: {region_s}/{year}") from e
    return _validate_pack_dict(raw, expect_region=region_s, expect_year=int(year))


def list_packs(
    *,
    region: Optional[str] = None,
    year: Optional[int] = None,
    root: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """E58 list + E64 optional region/year filter (case-insensitive region)."""
    base = root or PACKS_ROOT
    rows: list[dict[str, Any]] = []
    if not base.is_dir():
        return rows
    want_region = str(region).strip().upper() if region is not None and str(region).strip() else None
    want_year: Optional[int] = None
    if year is not None:
        try:
            want_year = int(year)
        except (TypeError, ValueError):
            want_year = None
    for region_dir in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("_")):
        region_name = region_dir.name.upper()
        if not _REGION_RE.match(region_name):
            continue
        if want_region is not None and region_name != want_region:
            continue
        for path in sorted(region_dir.glob("*.json")):
            try:
                year_i = int(path.stem)
            except ValueError:
                continue
            if want_year is not None and year_i != want_year:
                continue
            try:
                pack = load_pack(region_name, year_i, root=base)
            except (ValueError, FileNotFoundError, OSError):
                continue
            rows.append(
                {
                    "region": pack["region"],
                    "year": pack["year"],
                    "name": pack["name"],
                    "sourceNote": pack["sourceNote"],
                    "count": len(pack["holidays"]),
                }
            )
    rows.sort(key=lambda r: (r["region"], r["year"]))
    return rows


def pack_to_exceptions(pack: dict[str, Any]) -> list[dict[str, Any]]:
    holidays = pack.get("holidays") or []
    raw: list[dict[str, Any]] = []
    for h in holidays:
        if not isinstance(h, dict):
            continue
        entry: dict[str, Any] = {"date": h["date"], "kind": h["kind"]}
        if h.get("windows") is not None:
            entry["windows"] = h["windows"]
        raw.append(entry)
    return normalize_exceptions(raw)


def merge_exceptions_pack_wins(
    existing: Optional[list],
    pack_exceptions: Optional[list],
) -> dict[str, Any]:
    """Q3a: same date → pack wins; keep non-pack dates."""
    base = normalize_exceptions(existing or [])
    pack = normalize_exceptions(pack_exceptions or [])
    by_date: dict[str, dict[str, Any]] = {e["date"]: dict(e) for e in base}
    added: list[dict[str, Any]] = []
    replaced: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    pack_dates = {e["date"] for e in pack}
    for pe in pack:
        date_s = pe["date"]
        if date_s not in by_date:
            by_date[date_s] = dict(pe)
            added.append(dict(pe))
            continue
        prev = by_date[date_s]
        # compare kind + windows
        same_kind = prev.get("kind") == pe.get("kind")
        same_win = (prev.get("windows") or None) == (pe.get("windows") or None)
        if same_kind and same_win:
            unchanged.append(dict(prev))
        else:
            by_date[date_s] = dict(pe)
            replaced.append({"before": dict(prev), "after": dict(pe), "date": date_s})

    for e in base:
        if e["date"] not in pack_dates:
            unchanged.append(dict(e))

    merged = sorted(by_date.values(), key=lambda x: x["date"])
    if len(merged) > MAX_EXCEPTIONS:
        raise ValueError(f"exceptions 最多 {MAX_EXCEPTIONS} 条")
    return {
        "exceptions": merged,
        "added": added,
        "replaced": replaced,
        "unchanged": unchanged,
        "skipped": skipped,
    }


def upsert_applied_ledger(
    ledger: Optional[list],
    region: str,
    year: int,
    *,
    applied_at: Optional[str] = None,
) -> list[dict[str, Any]]:
    region_s = str(region).strip().upper()
    year_i = int(year)
    at = applied_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows: list[dict[str, Any]] = []
    if isinstance(ledger, list):
        for item in ledger:
            if not isinstance(item, dict):
                continue
            r = str(item.get("region", "")).strip().upper()
            try:
                y = int(item.get("year"))
            except (TypeError, ValueError):
                continue
            if r == region_s and y == year_i:
                continue
            rows.append(
                {
                    "region": r,
                    "year": y,
                    "appliedAt": str(item.get("appliedAt") or ""),
                }
            )
    rows.append({"region": region_s, "year": year_i, "appliedAt": at})
    rows.sort(key=lambda x: (x["region"], x["year"]))
    return rows


__all__ = [
    "PACKS_ROOT",
    "list_packs",
    "load_pack",
    "pack_to_exceptions",
    "merge_exceptions_pack_wins",
    "upsert_applied_ledger",
]
