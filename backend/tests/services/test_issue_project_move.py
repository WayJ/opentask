"""E80: pure helpers for project-move milestone integrity."""
from __future__ import annotations

import pytest

from opentask.services.issue_project_move import (
    ProjectMoveIntegrityResult,
    apply_project_move_integrity,
    milestone_for_duplicate,
)


def test_same_value_project_resubmit_does_not_clear_milestone():
    data = {"project_id": "p1", "title": "x"}
    meta = apply_project_move_integrity(
        data,
        existing_project_id="p1",
        existing_milestone_id="m1",
    )
    assert "milestone_id" not in data
    assert meta.milestone_cleared is False
    assert meta.milestone_from is None


def test_project_a_to_b_clears_milestone_when_not_explicit():
    data = {"project_id": "p2"}
    meta = apply_project_move_integrity(
        data,
        existing_project_id="p1",
        existing_milestone_id="m1",
    )
    assert data["milestone_id"] is None
    assert meta.milestone_cleared is True
    assert meta.milestone_from == "m1"


def test_project_to_null_clears_milestone():
    data = {"project_id": None}
    meta = apply_project_move_integrity(
        data,
        existing_project_id="p1",
        existing_milestone_id="m9",
    )
    assert data["milestone_id"] is None
    assert meta.milestone_cleared is True
    assert meta.milestone_from == "m9"


def test_explicit_milestone_in_payload_is_left_for_validation():
    data = {"project_id": "p2", "milestone_id": "m_b"}
    meta = apply_project_move_integrity(
        data,
        existing_project_id="p1",
        existing_milestone_id="m_a",
    )
    assert data["milestone_id"] == "m_b"
    # still report cleared-from-old for timeline if old existed and project changed
    # Q2a: explicit takes precedence for value; cleared flag only when we auto-null
    assert meta.milestone_cleared is False
    assert meta.milestone_from is None


def test_project_change_with_no_existing_milestone_sets_null_without_cleared_flag():
    data = {"project_id": "p2"}
    meta = apply_project_move_integrity(
        data,
        existing_project_id="p1",
        existing_milestone_id=None,
    )
    assert data["milestone_id"] is None
    assert meta.milestone_cleared is False


def test_no_project_key_is_noop():
    data = {"title": "only title"}
    meta = apply_project_move_integrity(
        data,
        existing_project_id="p1",
        existing_milestone_id="m1",
    )
    assert "milestone_id" not in data
    assert meta == ProjectMoveIntegrityResult()


def test_does_not_touch_cycle_id():
    data = {"project_id": "p2", "cycle_id": "c1"}
    apply_project_move_integrity(
        data,
        existing_project_id="p1",
        existing_milestone_id="m1",
    )
    assert data["cycle_id"] == "c1"


def test_milestone_for_duplicate_same_project_copies():
    assert (
        milestone_for_duplicate(
            source_project_id="p1",
            target_project_id="p1",
            source_milestone_id="m1",
        )
        == "m1"
    )


def test_milestone_for_duplicate_cross_project_null():
    assert (
        milestone_for_duplicate(
            source_project_id="p1",
            target_project_id="p2",
            source_milestone_id="m1",
        )
        is None
    )


def test_milestone_for_duplicate_to_null_project_null():
    assert (
        milestone_for_duplicate(
            source_project_id="p1",
            target_project_id=None,
            source_milestone_id="m1",
        )
        is None
    )
