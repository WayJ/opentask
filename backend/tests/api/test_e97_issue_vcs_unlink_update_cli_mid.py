"""E97 BE spy: no new issue-vcs routes; DELETE+PATCH present; neighbors untouched."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # backend/


def test_issue_vcs_router_has_delete_and_patch():
    text = (ROOT / "opentask/api/issue_vcs/router.py").read_text()
    assert 'router = APIRouter(prefix="/api/issues"' in text
    assert '@router.delete("/{issue_id}/vcs/links/{link_id}")' in text
    assert "async def delete_link" in text
    assert '@router.patch("/{issue_id}/vcs/links/{link_id}")' in text
    assert "async def update_link" in text
    # create/list/branch-name still present
    assert '@router.get("/{issue_id}/vcs/branch-name")' in text
    assert '@router.get("/{issue_id}/vcs/links")' in text
    assert '@router.post("/{issue_id}/vcs/links")' in text
    # VcsLinkUpdate camelCase fields
    assert "class VcsLinkUpdate" in text
    for field in ("branchName", "prUrl", "provider", "externalId", "status", "title"):
        assert field in text


def test_e97_no_new_alembic_versions_named_e97():
    versions = ROOT / "alembic" / "versions"
    assert versions.exists()
    names = [p.name for p in versions.glob("*.py")]
    assert not any("e97" in n.lower() for n in names)


def test_e97_no_new_initiative_health_route():
    text = (ROOT / "opentask/api/initiatives/router.py").read_text()
    assert '/health"' not in text
    assert "/health'" not in text
    assert "def get_initiative_health" not in text
    assert "def set_initiative_health" not in text


def test_e97_neighbor_surfaces_not_rewritten():
    """Smoke that key neighbor modules still exist with expected markers."""
    markers = [
        # E96 access-tokens
        ("opentask/api/access_token/__init__.py", 'router = APIRouter(prefix="/api/access-tokens"'),
        ("opentask/api/access_token/__init__.py", "async def create_access_token"),
        ("opentask/api/access_token/__init__.py", "async def list_access_tokens"),
        ("opentask/api/access_token/__init__.py", "async def delete_access_token"),
        # E95 project repos
        ("opentask/api/project/router.py", 'repo_router = APIRouter(prefix="/{project_id}/repos"'),
        ("opentask/api/project/router.py", "async def create_repo_config"),
        ("opentask/api/project/router.py", "async def list_repo_configs"),
        ("opentask/api/project/router.py", "async def get_repo_config"),
        ("opentask/api/project/router.py", "async def update_repo_config"),
        ("opentask/api/project/router.py", "async def delete_repo_config"),
        # E94 reactions
        ("opentask/api/issue/router.py", '@router.get("/{issue_id}/reactions")'),
        ("opentask/api/issue/router.py", "async def get_reactions"),
        ("opentask/api/issue/router.py", '@router.post("/{issue_id}/reactions")'),
        ("opentask/api/issue/router.py", "async def add_reaction"),
        ("opentask/api/issue/router.py", '@router.delete("/{issue_id}/reactions")'),
        ("opentask/api/issue/router.py", "async def remove_reaction"),
        ("opentask/api/issue/router.py", '@router.get("/{issue_id}/comments/{comment_id}/reactions")'),
        ("opentask/api/issue/router.py", "async def get_comment_reactions"),
        ("opentask/api/issue/router.py", '@router.post("/{issue_id}/comments/{comment_id}/reactions")'),
        ("opentask/api/issue/router.py", "async def add_comment_reaction"),
        ("opentask/api/issue/router.py", '@router.delete("/{issue_id}/comments/{comment_id}/reactions")'),
        ("opentask/api/issue/router.py", "async def remove_comment_reaction"),
        # E93 display-prefs
        ("opentask/api/display_prefs/router.py", '@router.get("/issue")'),
        ("opentask/api/display_prefs/router.py", '@router.put("/issue")'),
        ("opentask/api/display_prefs/router.py", "async def get_issue_display_prefs"),
        ("opentask/api/display_prefs/router.py", "async def put_issue_display_prefs"),
        # E92 saved-views write
        ("opentask/api/saved_views/router.py", '@router.post("")'),
        ("opentask/api/saved_views/router.py", "async def create_saved_view"),
        ("opentask/api/saved_views/router.py", '@router.patch("/{view_id}")'),
        ("opentask/api/saved_views/router.py", '@router.delete("/{view_id}")'),
        ("opentask/api/saved_views/router.py", '@router.post("/{view_id}/favorite")'),
        ("opentask/api/saved_views/router.py", '@router.post("/{view_id}/save-as")'),
        # E91 board-move
        ("opentask/api/issue/router.py", '@router.post("/board/move")'),
        ("opentask/api/issue/router.py", "async def move_issue_on_board"),
        # E90 initiative projects
        ("opentask/api/initiatives/router.py", '@router.put("/{initiative_id}/projects")'),
        ("opentask/api/initiatives/router.py", "async def set_projects"),
        ("opentask/api/initiatives/router.py", "async def attach_project"),
        ("opentask/api/initiatives/router.py", "async def detach_project"),
        # E89 CF reorder
        ("opentask/api/custom_fields/router.py", '@router.post("/reorder")'),
        ("opentask/api/custom_fields/router.py", "async def reorder_custom_fields"),
        # E88 favorites reorder
        ("opentask/api/favorites/router.py", '@router.put("/reorder")'),
        ("opentask/api/favorites/router.py", "async def reorder_favorites"),
        # E87 tag-groups / E86 replace_tags
        ("opentask/api/tags/router.py", 'groups_router = APIRouter(prefix="/api/tag-groups"'),
        ("opentask/api/tags/router.py", "async def update_tag"),
        ("opentask/api/issue/router.py", "async def replace_tags"),
        # E85–E79
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


def test_e97_formula_no_emit_guard_still_present():
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


def test_e97_no_requirement_repos_or_true_git_bound_to_epic():
    """E97 must not introduce requirement-repos CLI binding or /api/repositories git clone."""
    text = (ROOT / "opentask/api/issue_vcs/router.py").read_text()
    # docstring may mention "not Requirement/PGE"; assert no actual requirement-repos wiring
    assert "requirement-repos" not in text.lower()
    assert "requirement_repos" not in text.lower()
    assert "/api/repositories" not in text
    assert "git.clone" not in text.lower()
    assert "oauth2" not in text.lower()
    # no new e97-named repository router file
    assert not (ROOT / "opentask/api/repositories_e97").exists()
