"""E72: project template payload validate + offset→date."""
from __future__ import annotations

from datetime import date, datetime

import pytest
from fastapi import HTTPException

from opentask.services.project_template.service import (
    MAX_PROJECT_TEMPLATE_MILESTONES,
    compute_milestone_target_date,
    validate_project_template_payload,
)


def test_validate_normalizes_and_caps():
    out = validate_project_template_payload(
        {
            "description": "Ship",
            "milestones": [
                {"name": "Kickoff", "targetOffsetDays": 0},
                {"name": "Beta", "targetOffsetDays": 30},
            ],
        }
    )
    assert out["description"] == "Ship"
    assert out["milestones"][0]["position"] == 0
    assert out["milestones"][0]["name"] == "Kickoff"
    assert out["milestones"][0]["targetOffsetDays"] == 0
    assert out["milestones"][1]["targetOffsetDays"] == 30
    assert out["milestones"][1]["position"] == 1


def test_validate_none_payload():
    out = validate_project_template_payload(None)
    assert out == {"milestones": []}


def test_validate_rejects_over_30():
    payload = {"milestones": [{"name": f"M{i}"} for i in range(31)]}
    with pytest.raises(HTTPException) as ei:
        validate_project_template_payload(payload)
    assert ei.value.status_code == 400


def test_validate_rejects_empty_name():
    with pytest.raises(HTTPException) as ei:
        validate_project_template_payload({"milestones": [{"name": "  "}]})
    assert ei.value.status_code == 400


def test_validate_rejects_non_list_milestones():
    with pytest.raises(HTTPException) as ei:
        validate_project_template_payload({"milestones": "nope"})
    assert ei.value.status_code == 400


def test_offset_date():
    assert compute_milestone_target_date(base_date=date(2026, 1, 1), offset_days=None) is None
    dt = compute_milestone_target_date(base_date=date(2026, 1, 1), offset_days=30)
    assert dt == datetime(2026, 1, 31, 0, 0, 0)


def test_max_constant():
    assert MAX_PROJECT_TEMPLATE_MILESTONES == 30
