"""E90 CLI: initiative projects set + project attach|detach + version 1.79.0."""
from __future__ import annotations

import inspect
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_74_0():
    assert __version__ == "1.79.0"
    assert VERSION == "1.79.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.79.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.79.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.79.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.79.0" in result.output


def test_api_client_set_initiative_projects_uses_put_project_ids():
    assert hasattr(OpenTaskClient, "set_initiative_projects")
    src = inspect.getsource(OpenTaskClient.set_initiative_projects)
    assert "/api/initiatives/" in src
    assert "/projects" in src
    assert "self.put" in src
    assert "projectIds" in src
    # must not send snake_case JSON key
    assert '"project_ids"' not in src
    assert "'project_ids'" not in src
    # set must be PUT, not POST
    assert "self.post" not in src


def test_api_client_attach_detach_methods():
    assert hasattr(OpenTaskClient, "attach_initiative_project")
    assert hasattr(OpenTaskClient, "detach_initiative_project")
    attach_src = inspect.getsource(OpenTaskClient.attach_initiative_project)
    detach_src = inspect.getsource(OpenTaskClient.detach_initiative_project)
    assert "self.post" in attach_src
    assert "/projects/" in attach_src
    assert "self.delete" in detach_src
    assert "/projects/" in detach_src


def test_initiative_help_lists_projects_and_project():
    runner = CliRunner()
    result = runner.invoke(cli, ["initiative", "--help"])
    assert result.exit_code == 0
    assert "projects" in result.output
    assert "project" in result.output
    # E65 relations still present
    assert "relations" in result.output
    assert "relation" in result.output


def test_projects_set_help_lists_ids():
    runner = CliRunner()
    result = runner.invoke(cli, ["initiative", "projects", "set", "--help"])
    assert result.exit_code == 0
    assert "--ids" in result.output


def test_project_attach_detach_help():
    runner = CliRunner()
    attach = runner.invoke(cli, ["initiative", "project", "attach", "--help"])
    assert attach.exit_code == 0
    detach = runner.invoke(cli, ["initiative", "project", "detach", "--help"])
    assert detach.exit_code == 0


def _cfg(tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".opentask"
    cfg_dir.mkdir()
    monkeypatch.setattr(Config, "DEFAULT_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(Config, "CONFIG_FILE", cfg_dir / "config.json")
    cfg = Config()
    cfg.api_url = "http://localhost:7377"
    cfg.token = "tok"
    cfg.active_workspace_id = "ws-1"
    return cfg


def test_projects_set_ids_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_set(self, initiative_id, project_ids):
        called["id"] = initiative_id
        called["ids"] = list(project_ids)
        return {"id": initiative_id, "projectIds": list(project_ids)}

    monkeypatch.setattr(OpenTaskClient, "set_initiative_projects", fake_set)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["initiative", "projects", "set", "init-1", "--ids", "a,b,c", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert called.get("id") == "init-1"
    assert called.get("ids") == ["a", "b", "c"]
    assert "a" in result.output


def test_projects_set_empty_ids_clears(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_set(self, initiative_id, project_ids):
        called["ids"] = list(project_ids)
        return {"id": initiative_id, "projectIds": []}

    monkeypatch.setattr(OpenTaskClient, "set_initiative_projects", fake_set)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["initiative", "projects", "set", "init-2", "--ids", "", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert called.get("ids") == []


def test_projects_set_positional_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_set(self, initiative_id, project_ids):
        called["ids"] = list(project_ids)
        return {"id": initiative_id, "projectIds": list(project_ids)}

    monkeypatch.setattr(OpenTaskClient, "set_initiative_projects", fake_set)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["initiative", "projects", "set", "init-3", "p1", "p2", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert called.get("ids") == ["p1", "p2"]


def test_projects_set_requires_ids_or_positional(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["initiative", "projects", "set", "init-x"])
    assert result.exit_code != 0


def test_project_attach_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_attach(self, initiative_id, project_id):
        called["init"] = initiative_id
        called["proj"] = project_id
        return {"id": initiative_id, "projectIds": [project_id]}

    monkeypatch.setattr(OpenTaskClient, "attach_initiative_project", fake_attach)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["initiative", "project", "attach", "init-4", "proj-9", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert called.get("init") == "init-4"
    assert called.get("proj") == "proj-9"


def test_project_detach_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_detach(self, initiative_id, project_id):
        called["init"] = initiative_id
        called["proj"] = project_id
        return {"id": initiative_id, "projectIds": []}

    monkeypatch.setattr(OpenTaskClient, "detach_initiative_project", fake_detach)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["initiative", "project", "detach", "init-5", "proj-8", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert called.get("init") == "init-5"
    assert called.get("proj") == "proj-8"


def test_initiative_show_human_includes_projects(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_get(self, initiative_id):
        return {
            "id": initiative_id,
            "name": "Alpha",
            "status": "active",
            "description": "desc",
            "projectIds": ["p-aaa", "p-bbb"],
            "projects": [
                {"id": "p-aaa", "name": "Proj A"},
                {"id": "p-bbb", "name": "Proj B"},
            ],
        }

    monkeypatch.setattr(OpenTaskClient, "get_initiative", fake_get)

    runner = CliRunner()
    result = runner.invoke(cli, ["initiative", "show", "init-show"])
    assert result.exit_code == 0, result.output
    assert "Projects" in result.output or "Proj A" in result.output
