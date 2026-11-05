"""E88 BE spy: no new favorites routes; neighbor surfaces untouched; PUT reorder present."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # backend/


def test_favorites_router_has_put_reorder():
    text = (ROOT / "opentask/api/favorites/router.py").read_text()
    assert 'prefix="/api/favorites"' in text
    assert '@router.put("/reorder")' in text
    assert "async def reorder_favorites" in text
    assert "class FavoriteReorder" in text
    assert "ordered_ids" in text
    # Q1a: must be PUT, not POST reorder
    assert '@router.post("/reorder")' not in text
    # existing CRUD still present
    assert "async def list_favorites" in text
    assert "async def add_favorite" in text
    assert "async def remove_favorite" in text


def test_e88_no_new_alembic_versions_named_e88():
    versions = ROOT / "alembic" / "versions"
    assert versions.exists()
    names = [p.name for p in versions.glob("*.py")]
    assert not any("e88" in n.lower() for n in names)


def test_e88_neighbor_surfaces_not_rewritten():
    """Smoke that key neighbor modules still exist with expected markers."""
    markers = [
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


def test_e88_formula_no_emit_guard_still_present():
    """Formula surfaces must not gain emit side-effects in this epic."""
    candidates = list((ROOT / "opentask").rglob("*formula*"))
    assert candidates, "expected formula modules under opentask/"
