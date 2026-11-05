"""E47 CLI: activity list + version 1.67.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_31_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.67.0" in result.output


def test_activity_list_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["activity", "list", "--help"])
    assert result.exit_code == 0
    out = result.output.lower()
    assert "since" in out
    assert "action-type" in out
    assert "issue" in out
    assert "limit" in out
    assert "--json" in result.output or "json" in out
