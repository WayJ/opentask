"""E80: Issue project-move integrity — clear invalid milestone on project change."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ProjectMoveIntegrityResult:
    milestone_cleared: bool = False
    milestone_from: str | None = None


def apply_project_move_integrity(
    update_data: dict[str, Any],
    *,
    existing_project_id: str | None,
    existing_milestone_id: str | None,
) -> ProjectMoveIntegrityResult:
    """Q1a/Q2a: on real project_id change, auto-null milestone unless explicitly set.

    - Same-value re-submit → no-op.
    - Explicit ``milestone_id`` in payload → leave for caller validation (Q2a).
    - Never mutates ``cycle_id``.
    """
    if "project_id" not in update_data:
        return ProjectMoveIntegrityResult()

    new_project_id = update_data.get("project_id")
    if new_project_id == existing_project_id:
        return ProjectMoveIntegrityResult()

    if "milestone_id" in update_data:
        # Q2a: explicit value wins; validation happens elsewhere against new project
        return ProjectMoveIntegrityResult()

    update_data["milestone_id"] = None
    if existing_milestone_id:
        return ProjectMoveIntegrityResult(
            milestone_cleared=True,
            milestone_from=existing_milestone_id,
        )
    return ProjectMoveIntegrityResult()


def milestone_for_duplicate(
    *,
    source_project_id: str | None,
    target_project_id: str | None,
    source_milestone_id: str | None,
) -> str | None:
    """Q3a: same project → copy source milestone; cross-project / null target → None."""
    if target_project_id == source_project_id:
        return source_milestone_id
    return None
