"""E71: assignee_ids normalize — order-preserving dedupe; max 10."""
from __future__ import annotations

import pytest

from opentask.services.issue_assignee.service import (
    MAX_ISSUE_ASSIGNEES,
    normalize_assignee_ids,
)


def test_max_constant():
    assert MAX_ISSUE_ASSIGNEES == 10


def test_dedupe_preserves_order():
    assert normalize_assignee_ids(["a", "b", "a", "c"]) == ["a", "b", "c"]


def test_strips_empty():
    assert normalize_assignee_ids(["a", "", None, "  ", "b"]) == ["a", "b"]


def test_max_11_raises():
    ids = [f"u{i}" for i in range(11)]
    with pytest.raises(ValueError, match="max 10"):
        normalize_assignee_ids(ids)


def test_empty():
    assert normalize_assignee_ids([]) == []
    assert normalize_assignee_ids(None) == []
