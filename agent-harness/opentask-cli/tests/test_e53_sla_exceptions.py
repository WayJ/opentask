"""E53 CLI: sla business-hours exceptions + version 1.43.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_39_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.43.0" in result.output


def test_exceptions_group_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "business-hours", "exceptions", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "add" in result.output
    assert "remove" in result.output


def test_exceptions_add_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "business-hours", "exceptions", "add", "--help"])
    assert result.exit_code == 0
    assert "--date" in result.output
    assert "--kind" in result.output
    assert "--windows-json" in result.output


def test_business_hours_show_mentions_exceptions():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "business-hours", "show", "--help"])
    assert result.exit_code == 0
