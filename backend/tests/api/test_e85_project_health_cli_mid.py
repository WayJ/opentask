"""E85 BE spy: no new health routes; neighbor surfaces untouched; existing endpoints present."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # backend/


def test_project_router_still_has_health_and_timeline():
    text = (ROOT / "opentask/api/project/router.py").read_text()
    assert "health_router" in text
    assert "post_project_health" in text
    assert "get_project_health" in text
    assert "get_project_timeline" in text
    assert '@router.get("/{project_id}/timeline")' in text
    # Q1a: no bulk-health or other new mid routes
    assert "bulk-health" not in text
    assert "health-report" not in text


def test_e85_no_new_alembic_versions_named_e85():
    versions = ROOT / "alembic" / "versions"
    assert versions.exists()
    names = [p.name for p in versions.glob("*.py")]
    assert not any("e85" in n.lower() for n in names)


def test_e85_neighbor_surfaces_not_rewritten():
    """Smoke that key neighbor modules still exist with expected markers."""
    markers = {
        "opentask/api/cycles/router.py": "generate-upcoming",
        "opentask/services/project_watcher/service.py": "enrich_watchers",
        "opentask/api/issue_templates/router.py": "APIRouter",
        "opentask/services/milestone/service.py": "class MilestoneService",
        "opentask/services/issue_project_move.py": "apply_project_move_integrity",
    }
    for rel, marker in markers.items():
        path = ROOT / rel
        assert path.exists(), f"missing {rel}"
        assert marker in path.read_text(), f"{rel} missing marker {marker}"
