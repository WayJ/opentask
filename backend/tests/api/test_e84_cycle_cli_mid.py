"""E84 BE spy: no new cycle routes; neighbor surfaces untouched; existing endpoints present."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # backend/


def test_cycles_router_still_has_mid_endpoints():
    text = (ROOT / "opentask/api/cycles/router.py").read_text()
    assert '@router.post("/generate-upcoming")' in text
    assert "@router.patch(" in text and "{cycle_id}" in text
    assert "@router.delete(" in text
    # Q1a: no bulk-generate or other new mid routes
    assert "bulk-generate" not in text
    assert "generate-n" not in text


def test_e84_no_new_alembic_versions_named_e84():
    versions = ROOT / "alembic" / "versions"
    assert versions.exists()
    names = [p.name for p in versions.glob("*.py")]
    assert not any("e84" in n.lower() for n in names)


def test_e84_neighbor_surfaces_not_rewritten():
    """Smoke that key neighbor modules still exist with expected markers."""
    markers = {
        "opentask/services/project_watcher/service.py": "enrich_watchers",
        "opentask/api/issue_templates/router.py": "APIRouter",
        "opentask/services/milestone/service.py": "class MilestoneService",
        "opentask/services/issue_project_move.py": "apply_project_move_integrity",
    }
    for rel, marker in markers.items():
        path = ROOT / rel
        assert path.exists(), f"missing {rel}"
        assert marker in path.read_text(), f"{rel} missing marker {marker}"
