"""E79 CLI: project lead|member + version 1.63.0."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_63_0():
    assert __version__ == "1.63.0"
    assert VERSION == "1.63.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.63.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.63.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.63.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.63.0" in result.output


def test_project_lead_group_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "lead", "--help"])
    assert result.exit_code == 0, result.output
    assert "set" in result.output
    assert "clear" in result.output


def test_project_member_group_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "member", "--help"])
    assert result.exit_code == 0, result.output
    assert "add" in result.output
    assert "remove" in result.output
    assert "list" in result.output


def test_project_lead_set_calls_update():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.update_project = AsyncMock(
        return_value={"id": "proj-1", "lead_id": "user-1", "lead": {"id": "user-1", "name": "A"}}
    )
    with patch("opentask.core.project.OpenTaskClient", return_value=mock_client):
        result = runner.invoke(cli, ["project", "lead", "set", "proj-1", "user-1", "--json"])
    assert result.exit_code == 0, result.output
    assert mock_client.update_project.await_count == 1
    assert mock_client.update_project.await_args.kwargs.get("lead_id") == "user-1"


def test_project_lead_clear_sends_null():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.update_project = AsyncMock(
        return_value={"id": "proj-1", "lead_id": None, "lead": None}
    )
    with patch("opentask.core.project.OpenTaskClient", return_value=mock_client):
        result = runner.invoke(cli, ["project", "lead", "clear", "proj-1", "--json"])
    assert result.exit_code == 0, result.output
    assert mock_client.update_project.await_count == 1
    assert mock_client.update_project.await_args.kwargs.get("lead_id") is None


def test_project_member_add_remove_list():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.add_project_member = AsyncMock(return_value={"id": "user-2", "name": "B"})
    mock_client.remove_project_member = AsyncMock(return_value=True)
    mock_client.list_project_members = AsyncMock(return_value=[{"id": "user-2", "name": "B"}])
    mock_client.get_project = AsyncMock(
        return_value={"id": "proj-1", "lead_id": "user-1", "member_count": 1, "lead": {"id": "user-1"}}
    )
    with patch("opentask.core.project.OpenTaskClient", return_value=mock_client):
        r1 = runner.invoke(cli, ["project", "member", "add", "proj-1", "user-2", "--json"])
        r2 = runner.invoke(cli, ["project", "member", "list", "proj-1", "--json"])
        r3 = runner.invoke(cli, ["project", "member", "remove", "proj-1", "user-2", "--json"])
    assert r1.exit_code == 0, r1.output
    assert r2.exit_code == 0, r2.output
    assert r3.exit_code == 0, r3.output
    assert mock_client.add_project_member.await_count == 1
    assert mock_client.remove_project_member.await_count == 1
    assert mock_client.list_project_members.await_count == 1
