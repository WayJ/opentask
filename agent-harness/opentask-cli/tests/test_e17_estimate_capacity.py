"""E17: issue estimate_points + cycle capacity CLI."""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from opentask.opentask_cli import cli
from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config


def test_create_issue_passes_estimate_points(monkeypatch):
    runner = CliRunner()
    called = {}

    async def fake_create(self, **kwargs):
        called.update(kwargs)
        return {
            "id": "uuid-1",
            "issue_code": "OT-9",
            "title": kwargs.get("title"),
            "estimate_points": kwargs.get("estimate_points"),
            "status": "open",
            "type": "feature",
            "priority": "medium",
        }

    monkeypatch.setattr(OpenTaskClient, "create_issue", fake_create)
    result = runner.invoke(
        cli,
        ["issue", "create", "-t", "pts", "--estimate-points", "5", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert called.get("estimate_points") == 5.0


def test_update_issue_passes_estimate_points(monkeypatch):
    runner = CliRunner()
    called = {}

    async def fake_get(self, issue_id, by_code=False):
        return {"id": "uuid-1", "issue_code": "OT-9", "title": "t"}

    async def fake_update(self, issue_id, **kwargs):
        called["id"] = issue_id
        called["kwargs"] = kwargs
        return {
            "id": issue_id,
            "issue_code": "OT-9",
            "estimate_points": kwargs.get("estimate_points"),
        }

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get)
    monkeypatch.setattr(OpenTaskClient, "update_issue", fake_update)

    result = runner.invoke(
        cli,
        ["issue", "update", "OT-9", "--estimate-points", "8", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert called["kwargs"].get("estimate_points") == 8.0


@pytest.fixture
def runner_config(tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".opentask"
    cfg_dir.mkdir()
    monkeypatch.setattr(Config, "DEFAULT_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(Config, "CONFIG_FILE", cfg_dir / "config.json")
    cfg = Config()
    cfg.api_url = "http://localhost:7377"
    cfg.token = "tok"
    cfg.active_workspace_id = "ws-1"
    return cfg


def test_cycle_capacity_calls_hint(runner_config, monkeypatch):
    runner = CliRunner()
    called = {}

    async def fake_hint(self, cycle_id=None):
        called["cycle_id"] = cycle_id
        return {
            "basis": "history",
            "unit": "points",
            "suggestedCapacity": 13,
            "lookbackN": 3,
            "samples": [
                {
                    "cycleId": "c1",
                    "name": "C1",
                    "completedPoints": 13,
                    "completedIssueCount": 4,
                    "completedHours": 0,
                }
            ],
            "currentLoad": {"points": 5, "issueCount": 2, "hours": 0},
        }

    monkeypatch.setattr(OpenTaskClient, "get_cycle_capacity_hint", fake_hint)
    result = runner.invoke(cli, ["cycle", "capacity", "--cycle-id", "c1", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("cycle_id") == "c1"
    assert "points" in result.output
