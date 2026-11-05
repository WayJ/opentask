"""E64: holiday pack expansion — EU/UK + 2027 (TDD)."""
from __future__ import annotations

from opentask.services.sla.holiday_packs import list_packs, load_pack

REQUIRED = {
    ("CN", 2026),
    ("US", 2026),
    ("EU", 2026),
    ("UK", 2026),
    ("CN", 2027),
    ("US", 2027),
    ("EU", 2027),
    ("UK", 2027),
}


def test_list_contains_e64_keys_and_legacy():
    rows = list_packs()
    keys = {(r["region"], r["year"]) for r in rows}
    assert REQUIRED <= keys
    for region, year in (
        ("EU", 2026),
        ("UK", 2026),
        ("CN", 2027),
        ("US", 2027),
        ("EU", 2027),
        ("UK", 2027),
    ):
        row = next(r for r in rows if r["region"] == region and r["year"] == year)
        assert row["count"] >= 5 and row["name"] and row["sourceNote"]


def test_cn_2027_closed_only_pending_makeup():
    pack = load_pack("CN", 2027)
    assert all(h["kind"] == "closed" for h in pack["holidays"])
    assert "调休待补" in pack["sourceNote"]
    dates = {h["date"] for h in pack["holidays"]}
    assert "2027-01-01" in dates and "2027-02-06" in dates and "2027-10-01" in dates


def test_eu_uk_closed_and_uk_england_wales():
    eu = load_pack("EU", 2026)
    uk = load_pack("UK", 2026)
    assert all(h["kind"] == "closed" for h in eu["holidays"] + uk["holidays"])
    assert "England" in uk["sourceNote"] or "Wales" in uk["sourceNote"]
    assert "2026-04-03" in {h["date"] for h in uk["holidays"]}  # Good Friday
    assert "2026-05-01" in {h["date"] for h in eu["holidays"]}  # Labour Day


def test_us_2027_observed():
    pack = load_pack("US", 2027)
    dates = {h["date"] for h in pack["holidays"]}
    assert "2027-07-05" in dates  # Independence observed
    assert "2027-12-24" in dates  # Christmas observed
    assert all(h["kind"] == "closed" for h in pack["holidays"])


def test_list_packs_filter_region_year():
    rows = list_packs(region="eu", year=2027)
    assert rows and all(r["region"] == "EU" and r["year"] == 2027 for r in rows)
    assert list_packs(region="ZZ") == []
    assert len(list_packs()) >= 8
