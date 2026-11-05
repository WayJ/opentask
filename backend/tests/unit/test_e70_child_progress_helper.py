"""E70: childProgress pure helper — done=resolved|closed|rejected; 0 kids percent=null."""
from __future__ import annotations

from opentask.services.child_progress import (
    CHILD_PROGRESS_DONE_STATUSES,
    compute_child_progress,
)


def test_done_set_matches_e39():
    assert CHILD_PROGRESS_DONE_STATUSES == frozenset({"resolved", "closed", "rejected"})


def test_empty_percent_null():
    out = compute_child_progress([])
    assert out == {
        "total": 0,
        "done": 0,
        "open": 0,
        "percent": None,
        "byStatus": {},
    }


def test_mixed_five_children_percent_60():
    # 2 resolved + 1 closed + 2 open → done=3, total=5, percent=60
    statuses = ["resolved", "resolved", "closed", "open", "in_progress"]
    out = compute_child_progress(statuses)
    assert out["total"] == 5
    assert out["done"] == 3
    assert out["open"] == 2
    assert out["percent"] == 60
    assert out["byStatus"]["resolved"] == 2
    assert out["byStatus"]["closed"] == 1
    assert out["byStatus"]["open"] == 1
    assert out["byStatus"]["in_progress"] == 1


def test_all_done_percent_100():
    out = compute_child_progress(["resolved", "closed", "rejected"])
    assert out["total"] == 3
    assert out["done"] == 3
    assert out["open"] == 0
    assert out["percent"] == 100


def test_enum_like_value_attr():
    class S:
        def __init__(self, v):
            self.value = v

    out = compute_child_progress([S("resolved"), S("open")])
    assert out["done"] == 1
    assert out["total"] == 2
    assert out["percent"] == 50
