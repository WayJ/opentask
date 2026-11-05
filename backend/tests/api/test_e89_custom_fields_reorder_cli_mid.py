"""E89 BE spy: no new custom-fields routes; soft-update reorder; neighbor surfaces untouched."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # backend/


def test_custom_fields_router_has_post_reorder():
    text = (ROOT / "opentask/api/custom_fields/router.py").read_text()
    assert 'prefix="/api/custom-fields"' in text
    assert '@router.post("/reorder")' in text
    assert "async def reorder_custom_fields" in text
    assert "class CustomFieldReorder" in text
    assert "orderedIds" in text
    # Q1a: must be POST, not PUT reorder
    assert '@router.put("/reorder")' not in text
    # existing CRUD / validate still present
    assert "async def list_custom_fields" in text
    assert "async def create_custom_field" in text
    assert "async def validate_formula" in text


def test_custom_field_service_reorder_is_soft_update():
    """Unknown ids ignored; must NOT force full-set coverage like Favorites."""
    text = (ROOT / "opentask/services/custom_field/service.py").read_text()
    assert "async def reorder(" in text
    assert "if fid in by_id:" in text
    # soft-update marker: enumerate ordered_ids and only touch hits
    assert "for idx, fid in enumerate(ordered_ids):" in text


def test_e89_no_new_alembic_versions_named_e89():
    versions = ROOT / "alembic" / "versions"
    assert versions.exists()
    names = [p.name for p in versions.glob("*.py")]
    assert not any("e89" in n.lower() for n in names)


def test_e89_neighbor_surfaces_not_rewritten():
    """Smoke that key neighbor modules still exist with expected markers."""
    markers = [
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
    ]
    for rel, marker in markers:
        path = ROOT / rel
        assert path.exists(), f"missing {rel}"
        assert marker in path.read_text(), f"{rel} missing marker {marker}"


def test_e89_formula_no_emit_guard_still_present():
    """Formula surfaces must not gain emit side-effects in this epic."""
    candidates = list((ROOT / "opentask").rglob("*formula*"))
    assert candidates, "expected formula modules under opentask/"
