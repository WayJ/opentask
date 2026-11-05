"""E78 CLI: issue parent set|clear + version 1.71.0."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_62_0():
    assert __version__ == "1.71.0"
    assert VERSION == "1.71.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.71.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.71.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.71.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.71.0" in result.output


def test_issue_parent_group_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "parent", "--help"])
    assert result.exit_code == 0, result.output
    assert "set" in result.output
    assert "clear" in result.output


def test_issue_parent_set_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "parent", "set", "--help"])
    assert result.exit_code == 0, result.output
    assert "--json" in result.output


def test_issue_parent_clear_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "parent", "clear", "--help"])
    assert result.exit_code == 0, result.output
    assert "--json" in result.output


def test_issue_parent_set_calls_update():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.get_issue = AsyncMock(
        side_effect=[
            {"id": "child-uuid", "issue_code": "WAY-1"},
            {"id": "parent-uuid", "issue_code": "WAY-2"},
        ]
    )
    mock_client.update_issue = AsyncMock(
        return_value={
            "id": "child-uuid",
            "parent_issue_id": "parent-uuid",
            "issue_code": "WAY-1",
        }
    )
    with patch("opentask.core.issue.OpenTaskClient", return_value=mock_client):
        result = runner.invoke(cli, ["issue", "parent", "set", "WAY-1", "WAY-2", "--json"])
    assert result.exit_code == 0, result.output
    assert mock_client.update_issue.await_count == 1
    assert mock_client.update_issue.await_args.kwargs.get("parent_issue_id") == "parent-uuid"


def test_issue_parent_clear_sends_null():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.get_issue = AsyncMock(
        return_value={"id": "child-uuid", "issue_code": "WAY-1"}
    )
    mock_client.update_issue = AsyncMock(
        return_value={"id": "child-uuid", "parent_issue_id": None, "issue_code": "WAY-1"}
    )
    with patch("opentask.core.issue.OpenTaskClient", return_value=mock_client):
        result = runner.invoke(cli, ["issue", "parent", "clear", "WAY-1", "--json"])
    assert result.exit_code == 0, result.output
    assert mock_client.update_issue.await_count == 1
    assert mock_client.update_issue.await_args.kwargs.get("parent_issue_id") is None
