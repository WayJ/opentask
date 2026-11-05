"""E58: holiday pack loader/validate (TDD)."""
from __future__ import annotations

import pytest

from opentask.services.sla.holiday_packs import list_packs, load_pack, pack_to_exceptions


def test_list_contains_cn_us_2026():
    rows = list_packs()
    keys = {(r["region"], r["year"]) for r in rows}
    assert ("CN", 2026) in keys and ("US", 2026) in keys
    cn = next(r for r in rows if r["region"] == "CN" and r["year"] == 2026)
    assert cn["count"] > 10 and cn["name"] and cn["sourceNote"]


def test_load_cn_has_closed_and_forced_open():
    pack = load_pack("CN", 2026)
    assert pack["region"] == "CN" and pack["year"] == 2026
    kinds = {h["kind"] for h in pack["holidays"]}
    assert "closed" in kinds and "forced_open" in kinds
    dates = {h["date"] for h in pack["holidays"]}
    assert "2026-10-01" in dates and "2026-10-10" in dates  # National Day + makeup
    ex = pack_to_exceptions(pack)
    assert all("date" in e and e["kind"] in ("closed", "forced_open") for e in ex)


def test_load_us_closed_only_and_missing_404ish():
    pack = load_pack("US", 2026)
    assert all(h["kind"] == "closed" for h in pack["holidays"])
    assert "2026-11-26" in {h["date"] for h in pack["holidays"]}  # Thanksgiving
    with pytest.raises(FileNotFoundError):
        load_pack("ZZ", 2026)
    with pytest.raises(FileNotFoundError):
        load_pack("CN", 1999)


def test_unknown_kind_fails_load(tmp_path, monkeypatch):
    import json
    from opentask.services.sla import holiday_packs as hp

    bad = tmp_path / "XX"
    bad.mkdir()
    (bad / "2026.json").write_text(
        json.dumps(
            {
                "region": "XX",
                "year": 2026,
                "name": "Bad",
                "sourceNote": "t",
                "holidays": [{"date": "2026-01-01", "kind": "holiday"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hp, "PACKS_ROOT", tmp_path)
    with pytest.raises(ValueError, match="kind"):
        load_pack("XX", 2026)
