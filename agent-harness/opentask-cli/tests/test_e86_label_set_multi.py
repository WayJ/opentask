"""E86 CLI: label set|update + multi attach/detach + version 1.72.0."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_70_0():
    assert __version__ == "1.72.0"
    assert VERSION == "1.72.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.72.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.72.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.72.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.72.0" in result.output


def test_api_client_label_set_methods_exist():
    assert hasattr(OpenTaskClient, "replace_issue_tags")
    assert hasattr(OpenTaskClient, "update_tag")
    assert hasattr(OpenTaskClient, "attach_issue_tag")
    assert hasattr(OpenTaskClient, "detach_issue_tag")
    assert hasattr(OpenTaskClient, "list_issue_tags")


def test_label_help_lists_set_update_issue():
    runner = CliRunner()
    result = runner.invoke(cli, ["label", "--help"])
    assert result.exit_code == 0
    assert "set" in result.output
    assert "update" in result.output
    assert "issue" in result.output
    assert "attach" in result.output
    assert "detach" in result.output


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


def test_label_set_calls_replace(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_get_issue(self, ref, by_code=False):
        return {"id": "iss-1"}

    async def fake_replace(self, issue_id, tag_ids):
        called["id"] = issue_id
        called["tag_ids"] = list(tag_ids)
        return {"rows": [{"id": i} for i in tag_ids], "total": len(tag_ids)}

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get_issue)
    monkeypatch.setattr(OpenTaskClient, "replace_issue_tags", fake_replace)

    runner = CliRunner()
    result = runner.invoke(cli, ["label", "set", "OT-1", "--ids", "1,2,3", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("id") == "iss-1"
    assert called.get("tag_ids") == [1, 2, 3]
    assert "1" in result.output


def test_label_set_clear_empties(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_get_issue(self, ref, by_code=False):
        return {"id": "iss-2"}

    async def fake_replace(self, issue_id, tag_ids):
        called["tag_ids"] = list(tag_ids)
        return {"rows": [], "total": 0}

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get_issue)
    monkeypatch.setattr(OpenTaskClient, "replace_issue_tags", fake_replace)

    runner = CliRunner()
    result = runner.invoke(cli, ["label", "set", "iss-2", "--clear", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("tag_ids") == []


def test_label_set_empty_ids_clears(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_get_issue(self, ref, by_code=False):
        return {"id": "iss-3"}

    async def fake_replace(self, issue_id, tag_ids):
        called["tag_ids"] = list(tag_ids)
        return {"rows": [], "total": 0}

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get_issue)
    monkeypatch.setattr(OpenTaskClient, "replace_issue_tags", fake_replace)

    runner = CliRunner()
    result = runner.invoke(cli, ["label", "set", "iss-3", "--ids", "", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("tag_ids") == []


def test_label_set_requires_ids_or_clear(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["label", "set", "iss-x"])
    assert result.exit_code != 0


def test_label_update_calls_api(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_update(self, tag_id, *, name=None, color=None, group_id=None, clear_group=False):
        called["id"] = str(tag_id)
        called["name"] = name
        called["color"] = color
        called["group_id"] = group_id
        called["clear_group"] = clear_group
        return {"id": int(tag_id), "name": name, "color": color}

    monkeypatch.setattr(OpenTaskClient, "update_tag", fake_update)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["label", "update", "42", "--name", "bug", "--color", "#ff0000", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert called.get("id") == "42"
    assert called.get("name") == "bug"
    assert called.get("color") == "#ff0000"
    assert called.get("clear_group") is False


def test_label_update_clear_group(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_update(self, tag_id, *, name=None, color=None, group_id=None, clear_group=False):
        called["clear_group"] = clear_group
        called["group_id"] = group_id
        return {"id": int(tag_id), "name": "x"}

    monkeypatch.setattr(OpenTaskClient, "update_tag", fake_update)

    runner = CliRunner()
    result = runner.invoke(cli, ["label", "update", "7", "--clear-group", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("clear_group") is True


def test_label_attach_multi_tag_id(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    attached = []

    async def fake_get_issue(self, ref, by_code=False):
        return {"id": "iss-a"}

    async def fake_attach(self, issue_id, tag_id):
        attached.append((issue_id, str(tag_id)))
        return {"tag": {"id": int(tag_id)}}

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get_issue)
    monkeypatch.setattr(OpenTaskClient, "attach_issue_tag", fake_attach)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["label", "attach", "iss-a", "--tag-id", "1", "--tag-id", "2", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert attached == [("iss-a", "1"), ("iss-a", "2")]


def test_label_attach_positional_compat(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    attached = []

    async def fake_get_issue(self, ref, by_code=False):
        return {"id": "iss-b"}

    async def fake_attach(self, issue_id, tag_id):
        attached.append((issue_id, str(tag_id)))
        return {"tag": {"id": int(tag_id)}}

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get_issue)
    monkeypatch.setattr(OpenTaskClient, "attach_issue_tag", fake_attach)

    runner = CliRunner()
    result = runner.invoke(cli, ["label", "attach", "iss-b", "9", "--json"])
    assert result.exit_code == 0, result.output
    assert attached == [("iss-b", "9")]


def test_label_detach_multi_tag_id(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    detached = []

    async def fake_get_issue(self, ref, by_code=False):
        return {"id": "iss-d"}

    async def fake_detach(self, issue_id, tag_id):
        detached.append((issue_id, str(tag_id)))
        return None

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get_issue)
    monkeypatch.setattr(OpenTaskClient, "detach_issue_tag", fake_detach)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["label", "detach", "iss-d", "--tag-id", "3", "--tag-id", "4", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert detached == [("iss-d", "3"), ("iss-d", "4")]


def test_label_issue_lists_tags(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    called = {}

    async def fake_get_issue(self, ref, by_code=False):
        return {"id": "iss-l"}

    async def fake_list(self, issue_id):
        called["id"] = issue_id
        return {"rows": [{"id": 1, "name": "bug"}], "total": 1}

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get_issue)
    monkeypatch.setattr(OpenTaskClient, "list_issue_tags", fake_list)

    runner = CliRunner()
    result = runner.invoke(cli, ["label", "issue", "iss-l", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("id") == "iss-l"
    assert "bug" in result.output
