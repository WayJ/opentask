"""E80 CLI: issue update --project|--milestone|--clear-milestone + version 1.70.0."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_64_0():
    assert __version__ == "1.70.0"
    assert VERSION == "1.70.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.70.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.70.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.70.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.70.0" in result.output


def test_issue_update_help_has_project_milestone_flags():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "update", "--help"])
    assert result.exit_code == 0, result.output
    assert "--project" in result.output
    assert "--milestone" in result.output
    assert "--clear-milestone" in result.output


def test_issue_update_project_move_clears_milestone_in_response():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.get_issue = AsyncMock(
        return_value={"id": "iss-uuid", "issue_code": "WAY-1", "milestone_id": "m-old"}
    )
    mock_client.update_issue = AsyncMock(
        return_value={
            "id": "iss-uuid",
            "issue_code": "WAY-1",
            "project_id": "proj-b",
            "milestone_id": None,
        }
    )
    with patch("opentask.core.issue.OpenTaskClient", return_value=mock_client):
        result = runner.invoke(
            cli,
            ["issue", "update", "WAY-1", "--project", "proj-b", "--json"],
        )
    assert result.exit_code == 0, result.output
    assert mock_client.update_issue.await_count == 1
    kwargs = mock_client.update_issue.await_args.kwargs
    assert kwargs.get("project_id") == "proj-b"
    payload = json.loads(result.output)
    data = payload.get("data") or payload
    assert data.get("project_id") == "proj-b"
    assert data.get("milestone_id") in (None, "")


def test_issue_update_clear_project_sends_null():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.get_issue = AsyncMock(
        return_value={"id": "iss-uuid", "issue_code": "WAY-1"}
    )
    mock_client.update_issue = AsyncMock(
        return_value={
            "id": "iss-uuid",
            "issue_code": "WAY-1",
            "project_id": None,
            "milestone_id": None,
        }
    )
    with patch("opentask.core.issue.OpenTaskClient", return_value=mock_client):
        result = runner.invoke(
            cli,
            ["issue", "update", "WAY-1", "--project", "", "--json"],
        )
    assert result.exit_code == 0, result.output
    kwargs = mock_client.update_issue.await_args.kwargs
    assert kwargs.get("project_id") is None


def test_issue_update_milestone_and_clear_milestone():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.get_issue = AsyncMock(
        return_value={"id": "iss-uuid", "issue_code": "WAY-1"}
    )
    mock_client.update_issue = AsyncMock(
        return_value={
            "id": "iss-uuid",
            "issue_code": "WAY-1",
            "milestone_id": "m-new",
            "project_id": "p1",
        }
    )
    with patch("opentask.core.issue.OpenTaskClient", return_value=mock_client):
        result = runner.invoke(
            cli,
            ["issue", "update", "WAY-1", "--milestone", "m-new", "--json"],
        )
    assert result.exit_code == 0, result.output
    assert mock_client.update_issue.await_args.kwargs.get("milestone_id") == "m-new"

    mock_client.update_issue = AsyncMock(
        return_value={
            "id": "iss-uuid",
            "issue_code": "WAY-1",
            "milestone_id": None,
            "project_id": "p1",
        }
    )
    with patch("opentask.core.issue.OpenTaskClient", return_value=mock_client):
        result = runner.invoke(
            cli,
            ["issue", "update", "WAY-1", "--clear-milestone", "--json"],
        )
    assert result.exit_code == 0, result.output
    assert mock_client.update_issue.await_args.kwargs.get("milestone_id") is None


def test_issue_update_milestone_conflict_with_clear():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "issue",
            "update",
            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "--milestone",
            "m1",
            "--clear-milestone",
        ],
    )
    assert "mutually exclusive" in result.output
