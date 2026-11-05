"""E58: merge_exceptions_pack_wins + applied ledger (TDD)."""
from __future__ import annotations

from opentask.services.sla.holiday_packs import (
    merge_exceptions_pack_wins,
    upsert_applied_ledger,
)


def test_pack_wins_and_keeps_non_pack():
    existing = [
        {"date": "2026-10-01", "kind": "closed"},
        {"date": "2026-06-01", "kind": "closed"},
    ]
    pack = [
        {"date": "2026-10-01", "kind": "forced_open"},
        {"date": "2026-10-02", "kind": "closed"},
    ]
    out = merge_exceptions_pack_wins(existing, pack)
    by = {e["date"]: e for e in out["exceptions"]}
    assert by["2026-10-01"]["kind"] == "forced_open"
    assert "2026-06-01" in by and "2026-10-02" in by
    assert any(x["date"] == "2026-10-01" for x in out["replaced"])
    assert any(x["date"] == "2026-10-02" for x in out["added"])
    assert any(x["date"] == "2026-06-01" for x in out["unchanged"])


def test_idempotent_second_apply_unchanged():
    pack = [{"date": "2026-01-01", "kind": "closed"}]
    first = merge_exceptions_pack_wins([], pack)
    second = merge_exceptions_pack_wins(first["exceptions"], pack)
    assert second["exceptions"] == first["exceptions"]
    assert second["added"] == []
    assert any(x["date"] == "2026-01-01" for x in second["unchanged"])


def test_upsert_applied_ledger_updates_same_region_year():
    ledger = upsert_applied_ledger(None, "CN", 2026, applied_at="2026-01-01T00:00:00Z")
    assert ledger == [{"region": "CN", "year": 2026, "appliedAt": "2026-01-01T00:00:00Z"}]
    ledger2 = upsert_applied_ledger(ledger, "CN", 2026, applied_at="2026-02-01T00:00:00Z")
    assert len(ledger2) == 1 and ledger2[0]["appliedAt"] == "2026-02-01T00:00:00Z"
    ledger3 = upsert_applied_ledger(ledger2, "US", 2026, applied_at="2026-03-01T00:00:00Z")
    assert {(r["region"], r["year"]) for r in ledger3} == {("CN", 2026), ("US", 2026)}
