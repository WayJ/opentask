"""E86 BE spy: no new tag routes; neighbor surfaces untouched; existing endpoints present."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # backend/


def test_issue_router_still_has_tag_replace_attach_detach():
    text = (ROOT / "opentask/api/issue/router.py").read_text()
    assert "async def replace_tags" in text
    assert "async def add_tag" in text
    assert "async def remove_tag" in text
    assert "async def get_tags" in text
    assert '@router.put("/{issue_id}/tags")' in text
    assert '@router.post("/{issue_id}/tags/{tag_id}")' in text
    assert '@router.delete("/{issue_id}/tags/{tag_id}")' in text
    # Q1a: no bulk-label or other new mid routes
    assert "bulk-tags" not in text
    assert "label-set" not in text


def test_tags_router_still_has_update_tag():
    text = (ROOT / "opentask/api/tags/router.py").read_text()
    assert "async def update_tag" in text
    assert '@tags_router.patch("/{tag_id}")' in text
    assert "clear_group" in text


def test_e86_no_new_alembic_versions_named_e86():
    versions = ROOT / "alembic" / "versions"
    assert versions.exists()
    names = [p.name for p in versions.glob("*.py")]
    assert not any("e86" in n.lower() for n in names)


def test_e86_neighbor_surfaces_not_rewritten():
    """Smoke that key neighbor modules still exist with expected markers."""
    markers = {
        "opentask/api/project/router.py": "get_project_health",
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
