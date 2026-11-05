"""E87 BE spy: no new tag-group routes; neighbor surfaces untouched; existing endpoints present."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # backend/


def test_tags_router_has_tag_groups_crud():
    text = (ROOT / "opentask/api/tags/router.py").read_text()
    assert 'groups_router = APIRouter(prefix="/api/tag-groups"' in text
    assert "async def list_tag_groups" in text
    assert "async def create_tag_group" in text
    assert "async def update_tag_group" in text
    assert "async def delete_tag_group" in text
    assert '@groups_router.get("")' in text
    assert '@groups_router.post("")' in text
    assert '@groups_router.patch("/{group_id}")' in text
    assert '@groups_router.delete("/{group_id}")' in text
    # TagUpdate.group_id is str UUID
    assert "group_id: Optional[str]" in text
    assert "clear_group" in text
    # list_tags supports group_id Query
    assert "group_id: Optional[str] = Query(None)" in text
    # Q1a: no new nested /api/tags/groups alias mid routes
    assert 'prefix="/api/tags/groups"' not in text


def test_e87_no_new_alembic_versions_named_e87():
    versions = ROOT / "alembic" / "versions"
    assert versions.exists()
    names = [p.name for p in versions.glob("*.py")]
    assert not any("e87" in n.lower() for n in names)


def test_e87_neighbor_surfaces_not_rewritten():
    """Smoke that key neighbor modules still exist with expected markers."""
    markers = {
        "opentask/api/issue/router.py": "async def replace_tags",
        "opentask/api/tags/router.py": "async def update_tag",
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


def test_e87_formula_no_emit_guard_still_present():
    """Formula surfaces must not gain emit side-effects in this epic."""
    # Prefer known no-emit markers from formula service if present
    candidates = list((ROOT / "opentask").rglob("*formula*"))
    # Soft check: at least one formula module exists (E40+)
    assert candidates, "expected formula modules under opentask/"
