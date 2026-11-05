"""E94 BE spy: no new reaction routes; six endpoints present; neighbors untouched."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # backend/


def test_issue_router_has_six_reaction_endpoints():
    text = (ROOT / "opentask/api/issue/router.py").read_text()
    assert '@router.get("/{issue_id}/reactions")' in text
    assert "async def get_reactions" in text
    assert '@router.post("/{issue_id}/reactions")' in text
    assert "async def add_reaction" in text
    assert '@router.delete("/{issue_id}/reactions")' in text
    assert "async def remove_reaction" in text
    assert '@router.get("/{issue_id}/comments/{comment_id}/reactions")' in text
    assert "async def get_comment_reactions" in text
    assert '@router.post("/{issue_id}/comments/{comment_id}/reactions")' in text
    assert "async def add_comment_reaction" in text
    assert '@router.delete("/{issue_id}/comments/{comment_id}/reactions")' in text
    assert "async def remove_comment_reaction" in text


def test_e94_no_new_alembic_versions_named_e94():
    versions = ROOT / "alembic" / "versions"
    assert versions.exists()
    names = [p.name for p in versions.glob("*.py")]
    assert not any("e94" in n.lower() for n in names)


def test_e94_no_new_initiative_health_route():
    text = (ROOT / "opentask/api/initiatives/router.py").read_text()
    assert '/health"' not in text
    assert "/health'" not in text
    assert "def get_initiative_health" not in text
    assert "def set_initiative_health" not in text


def test_e94_neighbor_surfaces_not_rewritten():
    """Smoke that key neighbor modules still exist with expected markers."""
    markers = [
        ("opentask/api/display_prefs/router.py", '@router.get("/issue")'),
        ("opentask/api/display_prefs/router.py", '@router.put("/issue")'),
        ("opentask/api/display_prefs/router.py", "async def get_issue_display_prefs"),
        ("opentask/api/display_prefs/router.py", "async def put_issue_display_prefs"),
        ("opentask/api/saved_views/router.py", '@router.post("")'),
        ("opentask/api/saved_views/router.py", "async def create_saved_view"),
        ("opentask/api/saved_views/router.py", '@router.patch("/{view_id}")'),
        ("opentask/api/saved_views/router.py", '@router.delete("/{view_id}")'),
        ("opentask/api/saved_views/router.py", '@router.post("/{view_id}/favorite")'),
        ("opentask/api/saved_views/router.py", '@router.post("/{view_id}/save-as")'),
        ("opentask/api/issue/router.py", '@router.post("/board/move")'),
        ("opentask/api/issue/router.py", "async def move_issue_on_board"),
        ("opentask/api/initiatives/router.py", '@router.put("/{initiative_id}/projects")'),
        ("opentask/api/initiatives/router.py", "async def set_projects"),
        ("opentask/api/initiatives/router.py", "async def attach_project"),
        ("opentask/api/initiatives/router.py", "async def detach_project"),
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


def test_e94_formula_no_emit_guard_still_present():
    """Formula surfaces must not gain emit side-effects in this epic."""
    candidates = list((ROOT / "opentask").rglob("*formula*"))
    assert candidates, "expected formula modules under opentask/"
    for path in candidates:
        if path.suffix != ".py":
            continue
        text = path.read_text()
        lowered = text.lower()
        if "emit" in lowered:
            assert "emit_activity_push" not in text
            assert (
                "emit_webhook" not in text
                or "no-emit" in lowered
                or "no_emit" in lowered
                or "never emit" in lowered
            )
