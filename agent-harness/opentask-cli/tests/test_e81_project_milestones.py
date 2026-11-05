"""E81 CLI: project milestone CRUD + issue create/list --milestone + version 1.66.0."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_66_0():
    assert __version__ == "1.66.0"
    assert VERSION == "1.66.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.66.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.66.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.66.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.66.0" in result.output


def test_project_milestone_group_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "milestone", "--help"])
    assert result.exit_code == 0, result.output
    for name in ("list", "create", "show", "update", "delete"):
        assert name in result.output


def test_project_milestone_list_create_show_update_delete():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.list_project_milestones = AsyncMock(
        return_value=[{"id": "ms-1", "name": "M1", "issue_count": 0, "status": "planned"}]
    )
    mock_client.create_project_milestone = AsyncMock(
        return_value={"id": "ms-1", "name": "M1", "issue_count": 0, "status": "planned"}
    )
    mock_client.get_project_milestone = AsyncMock(
        return_value={"id": "ms-1", "name": "M1", "issue_count": 2, "status": "planned"}
    )
    mock_client.update_project_milestone = AsyncMock(
        return_value={"id": "ms-1", "name": "M2", "issue_count": 2, "status": "done"}
    )
    mock_client.delete_project_milestone = AsyncMock(return_value=True)

    with patch("opentask.core.project.OpenTaskClient", return_value=mock_client):
        r_list = runner.invoke(
            cli, ["project", "milestone", "list", "proj-1", "--status", "planned", "--json"]
        )
        r_create = runner.invoke(
            cli,
            [
                "project",
                "milestone",
                "create",
                "proj-1",
                "--name",
                "M1",
                "--status",
                "planned",
                "--json",
            ],
        )
        r_show = runner.invoke(
            cli, ["project", "milestone", "show", "proj-1", "ms-1", "--json"]
        )
        r_update = runner.invoke(
            cli,
            [
                "project",
                "milestone",
                "update",
                "proj-1",
                "ms-1",
                "--name",
                "M2",
                "--status",
                "done",
                "--json",
            ],
        )
        r_delete = runner.invoke(
            cli, ["project", "milestone", "delete", "proj-1", "ms-1", "--json"]
        )

    assert r_list.exit_code == 0, r_list.output
    assert r_create.exit_code == 0, r_create.output
    assert r_show.exit_code == 0, r_show.output
    assert r_update.exit_code == 0, r_update.output
    assert r_delete.exit_code == 0, r_delete.output

    assert mock_client.list_project_milestones.await_count == 1
    assert mock_client.list_project_milestones.await_args.kwargs.get("status") == "planned"
    assert mock_client.create_project_milestone.await_count == 1
    assert mock_client.create_project_milestone.await_args.args[0] == "proj-1"
    assert mock_client.create_project_milestone.await_args.kwargs.get("name") == "M1"
    assert mock_client.get_project_milestone.await_count == 1
    assert mock_client.update_project_milestone.await_count == 1
    assert mock_client.update_project_milestone.await_args.kwargs.get("name") == "M2"
    assert mock_client.update_project_milestone.await_args.kwargs.get("status") == "done"
    assert mock_client.delete_project_milestone.await_count == 1


def test_issue_create_passes_milestone():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.create_issue = AsyncMock(
        return_value={"id": "iss-1", "title": "T", "milestone_id": "ms-1", "issue_code": "OT-1"}
    )
    with patch("opentask.core.issue.OpenTaskClient", return_value=mock_client):
        result = runner.invoke(
            cli,
            [
                "issue",
                "create",
                "-t",
                "T",
                "--project",
                "proj-1",
                "--milestone",
                "ms-1",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.output
    assert mock_client.create_issue.await_count == 1
    assert mock_client.create_issue.await_args.kwargs.get("milestone_id") == "ms-1"


def test_issue_list_passes_milestone_and_none():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.list_issues = AsyncMock(return_value={"rows": [], "total": 0})
    with patch("opentask.core.issue.OpenTaskClient", return_value=mock_client):
        r1 = runner.invoke(cli, ["issue", "list", "--milestone", "ms-1", "--json"])
        r2 = runner.invoke(cli, ["issue", "list", "--milestone", "__none__", "--json"])
    assert r1.exit_code == 0, r1.output
    assert r2.exit_code == 0, r2.output
    assert mock_client.list_issues.await_count == 2
    assert mock_client.list_issues.await_args_list[0].kwargs.get("milestone_id") == "ms-1"
    assert mock_client.list_issues.await_args_list[1].kwargs.get("milestone_id") == "__none__"
