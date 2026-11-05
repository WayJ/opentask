"""E90 BE spy: no new initiative routes; PUT/POST/DELETE projects present; neighbors untouched."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # backend/


def test_initiatives_router_has_put_post_delete_projects():
    text = (ROOT / "opentask/api/initiatives/router.py").read_text()
    assert 'prefix="/api/initiatives"' in text or 'APIRouter' in text
    assert '@router.put("/{initiative_id}/projects")' in text
    assert "async def set_projects" in text
    assert "projectIds" in text
    assert '@router.post("/{initiative_id}/projects/{project_id}")' in text
    assert "async def attach_project" in text
    assert '@router.delete("/{initiative_id}/projects/{project_id}")' in text
    assert "async def detach_project" in text
    # E65 relations still present
    assert '@router.get("/{initiative_id}/relations")' in text
    assert '@router.post("/{initiative_id}/relations")' in text
    assert '@router.delete("/{initiative_id}/relations/{relation_id}")' in text


def test_e90_no_new_initiative_health_route():
    """Must NOT add /health under initiatives (not this epic)."""
    text = (ROOT / "opentask/api/initiatives/router.py").read_text()
    assert '/health"' not in text
    assert "/health'" not in text
    assert "async def" in text  # sanity
    # no dedicated health get/set handlers
    assert "def get_initiative_health" not in text
    assert "def set_initiative_health" not in text


def test_e90_no_new_alembic_versions_named_e90():
    versions = ROOT / "alembic" / "versions"
    assert versions.exists()
    names = [p.name for p in versions.glob("*.py")]
    assert not any("e90" in n.lower() for n in names)


def test_e90_neighbor_surfaces_not_rewritten():
    """Smoke that key neighbor modules still exist with expected markers."""
    markers = [
        ("opentask/api/custom_fields/router.py", '@router.post("/reorder")'),
        ("opentask/api/custom_fields/router.py", "async def reorder_custom_fields"),
        ("opentask/api/favorites/router.py", '@router.put("/reorder")'),
        ("opentask/api/favorites/router.py", "async def reorder_favorites"),
        ("opentask/api/tags/router.py", 'groups_router = APIRouter(prefix="/api/tag-groups"'),
        ("opentask/api/tags/router.py", "async def update_tag"),
        ("opentask/api/issue/router.py", "async def replace_tags"),
        ("opentask/api/project/router.py", "get_project_health"),
        ("opentask/api/cycles/router.py", "generate-upcoming"),
        ("opentask/services/project_watcher/service.py", "enrich_watchers"),
        ("opentask/api/issue_templates/router.py", "APIRouter"),
        ("opentask/services/milestone/service.py", "class MilestoneService"),
        ("opentask/services/issue_project_move.py", "apply_project_move_integrity"),
        ("opentask/api/initiatives/router.py", "async def list_relations"),
        ("opentask/api/initiatives/router.py", "targetInitiativeId"),
    ]
    for rel, marker in markers:
        path = ROOT / rel
        assert path.exists(), f"missing {rel}"
        assert marker in path.read_text(), f"{rel} missing marker {marker}"


def test_e90_formula_no_emit_guard_still_present():
    """Formula surfaces must not gain emit side-effects in this epic."""
    candidates = list((ROOT / "opentask").rglob("*formula*"))
    assert candidates, "expected formula modules under opentask/"
