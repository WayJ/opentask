"""E95 CLI: project repo list|show|add|update|remove + version 1.79.0."""
from __future__ import annotations

import inspect
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]

PROJECT = "deadbeef-0000-0000-0000-0000000000aa"
REPO_ID = "42"


def test_version_pins_1_79_0():
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


def test_api_client_list_project_repos():
    assert hasattr(OpenTaskClient, "list_project_repos")
    src = inspect.getsource(OpenTaskClient.list_project_repos)
    assert "/api/projects/" in src
    assert "/repos" in src
    assert "self.get" in src


def test_api_client_get_project_repo():
    assert hasattr(OpenTaskClient, "get_project_repo")
    src = inspect.getsource(OpenTaskClient.get_project_repo)
    assert "/repos/" in src
    assert "self.get" in src


def test_api_client_create_project_repo_body():
    assert hasattr(OpenTaskClient, "create_project_repo")
    src = inspect.getsource(OpenTaskClient.create_project_repo)
    assert "/repos" in src
    assert "self.post" in src
    assert '"name"' in src or "'name'" in src
    assert '"url"' in src or "'url'" in src
    assert '"main_branch"' in src or "'main_branch'" in src
    assert '"project_id"' in src or "'project_id'" in src


def test_api_client_update_project_repo_put():
    assert hasattr(OpenTaskClient, "update_project_repo")
    src = inspect.getsource(OpenTaskClient.update_project_repo)
    assert "/repos/" in src
    assert "self.put" in src


def test_api_client_delete_project_repo():
    assert hasattr(OpenTaskClient, "delete_project_repo")
    src = inspect.getsource(OpenTaskClient.delete_project_repo)
    assert "/repos/" in src
    assert "self.delete" in src


def test_project_help_lists_repo_group():
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "--help"])
    assert result.exit_code == 0
    assert "repo" in result.output
    # neighbors still present
    assert "milestone" in result.output
    assert "health" in result.output
    assert "lead" in result.output
    assert "member" in result.output


def test_project_repo_help_lists_commands():
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "repo", "--help"])
    assert result.exit_code == 0
    for name in ("list", "show", "add", "update", "remove"):
        assert name in result.output


def test_reaction_and_display_prefs_still_in_help():
    runner = CliRunner()
    rx = runner.invoke(cli, ["issue", "reaction", "--help"])
    assert rx.exit_code == 0
    assert "list" in rx.output
    assert "add" in rx.output
    dp = runner.invoke(cli, ["display-prefs", "--help"])
    assert dp.exit_code == 0
    assert "get" in dp.output
    assert "set" in dp.output


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


def test_project_repo_list_empty(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {"n": 0}

    async def fake_list(self, project_id):
        called["n"] += 1
        called["id"] = project_id
        return []

    monkeypatch.setattr(OpenTaskClient, "list_project_repos", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "repo", "list", PROJECT])
    assert result.exit_code == 0, result.output
    assert called["n"] == 1
    assert called["id"] == PROJECT
    out = result.output.lower()
    assert "无" in result.output or "empty" in out or "0" in result.output or "none" in out or "no " in out


def test_project_repo_list_human_table(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_list(self, project_id):
        return [
            {
                "id": 7,
                "name": "backend",
                "url": "https://github.com/acme/backend.git",
                "main_branch": "main",
            }
        ]

    monkeypatch.setattr(OpenTaskClient, "list_project_repos", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "repo", "list", PROJECT])
    assert result.exit_code == 0, result.output
    assert "backend" in result.output
    assert "github.com/acme/backend.git" in result.output
    assert "main" in result.output


def test_project_repo_list_json(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_list(self, project_id):
        return [{"id": 1, "name": "fe", "url": "u", "main_branch": "dev"}]

    monkeypatch.setattr(OpenTaskClient, "list_project_repos", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "repo", "list", PROJECT, "--json"])
    assert result.exit_code == 0, result.output
    assert "fe" in result.output
    assert "rows" in result.output or "dev" in result.output


def test_project_repo_show_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_get(self, project_id, repo_id):
        called["pid"] = project_id
        called["rid"] = str(repo_id)
        return {
            "id": 42,
            "name": "api",
            "url": "https://example.com/api.git",
            "main_branch": "main",
        }

    monkeypatch.setattr(OpenTaskClient, "get_project_repo", fake_get)
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "repo", "show", PROJECT, REPO_ID])
    assert result.exit_code == 0, result.output
    assert called.get("pid") == PROJECT
    assert called.get("rid") == REPO_ID
    assert "api" in result.output
    assert "main" in result.output


def test_project_repo_add_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_create(self, project_id, *, name, url, main_branch="main"):
        called["pid"] = project_id
        called["name"] = name
        called["url"] = url
        called["main_branch"] = main_branch
        return {"id": 9, "name": name, "url": url, "main_branch": main_branch}

    monkeypatch.setattr(OpenTaskClient, "create_project_repo", fake_create)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "project",
            "repo",
            "add",
            PROJECT,
            "--name",
            "svc",
            "--url",
            "https://gh/s.git",
            "--main-branch",
            "develop",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("pid") == PROJECT
    assert called.get("name") == "svc"
    assert called.get("url") == "https://gh/s.git"
    assert called.get("main_branch") == "develop"
    assert "svc" in result.output


def test_project_repo_add_default_main_branch(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_create(self, project_id, *, name, url, main_branch="main"):
        called["main_branch"] = main_branch
        return {"id": 1, "name": name, "url": url, "main_branch": main_branch}

    monkeypatch.setattr(OpenTaskClient, "create_project_repo", fake_create)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["project", "repo", "add", PROJECT, "--name", "x", "--url", "https://x.git"],
    )
    assert result.exit_code == 0, result.output
    assert called.get("main_branch") == "main"


def test_project_repo_add_missing_name_no_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_create(self, *a, **k):
        raise AssertionError("should not call api without --name")

    monkeypatch.setattr(OpenTaskClient, "create_project_repo", fake_create)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["project", "repo", "add", PROJECT, "--url", "https://x.git"]
    )
    assert result.exit_code != 0


def test_project_repo_add_missing_url_no_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_create(self, *a, **k):
        raise AssertionError("should not call api without --url")

    monkeypatch.setattr(OpenTaskClient, "create_project_repo", fake_create)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["project", "repo", "add", PROJECT, "--name", "x"]
    )
    assert result.exit_code != 0


def test_project_repo_update_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_update(self, project_id, repo_id, **fields):
        called["pid"] = project_id
        called["rid"] = str(repo_id)
        called["fields"] = fields
        return {"id": int(repo_id), "name": fields.get("name", "n"), **fields}

    monkeypatch.setattr(OpenTaskClient, "update_project_repo", fake_update)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "project",
            "repo",
            "update",
            PROJECT,
            REPO_ID,
            "--name",
            "renamed",
            "--main-branch",
            "trunk",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called.get("pid") == PROJECT
    assert called.get("rid") == REPO_ID
    assert called.get("fields", {}).get("name") == "renamed"
    assert called.get("fields", {}).get("main_branch") == "trunk"


def test_project_repo_update_no_flags_no_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    async def fake_update(self, *a, **k):
        raise AssertionError("should not call api with no change flags")

    monkeypatch.setattr(OpenTaskClient, "update_project_repo", fake_update)
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "repo", "update", PROJECT, REPO_ID])
    assert result.exit_code != 0


def test_project_repo_remove_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_rm(self, project_id, repo_id):
        called["pid"] = project_id
        called["rid"] = str(repo_id)
        return True

    monkeypatch.setattr(OpenTaskClient, "delete_project_repo", fake_rm)
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "repo", "remove", PROJECT, REPO_ID])
    assert result.exit_code == 0, result.output
    assert called.get("pid") == PROJECT
    assert called.get("rid") == REPO_ID


def test_project_repo_rm_alias(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {"n": 0}

    async def fake_rm(self, project_id, repo_id):
        called["n"] += 1
        return True

    monkeypatch.setattr(OpenTaskClient, "delete_project_repo", fake_rm)
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "repo", "rm", PROJECT, REPO_ID])
    assert result.exit_code == 0, result.output
    assert called["n"] == 1
