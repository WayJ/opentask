"""E24 CLI: insights summary + version 1.18.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_8_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.18.0" in result.output


def test_insights_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["insights", "--help"])
    assert result.exit_code == 0
    assert "summary" in result.output


def test_insights_summary_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["insights", "summary", "--help"])
    assert result.exit_code == 0
    assert "--cycle" in result.output
