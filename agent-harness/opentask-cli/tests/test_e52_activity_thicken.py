"""E52 CLI: activity --watching + unread + version 1.38.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_36_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.38.0" in result.output


def test_activity_list_watching_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["activity", "list", "--help"])
    assert result.exit_code == 0
    out = result.output.lower()
    assert "watching" in out
    assert "since" in out


def test_activity_unread_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["activity", "unread", "--help"])
    assert result.exit_code == 0
    out = result.output.lower()
    assert "watching" in out or "unread" in out
