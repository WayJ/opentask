"""E19: issue list --mine / --watching / --due-soon"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from click.testing import CliRunner

from opentask.opentask_cli import cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config


def test_api_client_list_issues_e19_params():
    client = OpenTaskClient(base_url="http://x", token="t")
    client.get = AsyncMock(return_value={"rows": [], "total": 0})

    async def _run():
        await client.list_issues(watching=True, due_soon=True, assignee_id="me")
        args, kwargs = client.get.await_args
        assert args[0] == "/api/issues"
        params = kwargs["params"]
        assert params["watching"] == "true"
        assert params["due_soon"] == "true"
        assert params["assignee_id"] == "me"

    asyncio.run(_run())


def test_cli_mine_watching_due_soon_flags(tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".opentask"
    cfg_dir.mkdir()
    monkeypatch.setattr(Config, "DEFAULT_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(Config, "CONFIG_FILE", cfg_dir / "config.json")
    cfg = Config()
    cfg.api_url = "http://localhost:7377"
    cfg.token = "tok"
    cfg.active_workspace_id = "ws-1"

    called = {}

    async def fake_list(self, **kwargs):
        called.update(kwargs)
        return {"rows": [], "total": 0}

    monkeypatch.setattr(OpenTaskClient, "list_issues", fake_list)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["issue", "list", "--mine", "--watching", "--due-soon", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert called.get("assignee_id") == "me"
    assert called.get("watching") is True
    assert called.get("due_soon") is True
