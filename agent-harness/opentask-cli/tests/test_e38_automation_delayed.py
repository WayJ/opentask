"""E38 CLI: automation run-due|pending + delay_minutes help + version 1.54.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_22_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.54.0" in result.output


def test_automation_run_due_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["automation", "run-due", "--help"])
    assert result.exit_code == 0
    assert "run-due" in result.output
    assert "延迟" in result.output or "due" in result.output.lower()


def test_automation_pending_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["automation", "pending", "--help"])
    assert result.exit_code == 0
    assert "--status" in result.output


def test_automation_create_help_mentions_delay():
    runner = CliRunner()
    result = runner.invoke(cli, ["automation", "create", "--help"])
    assert result.exit_code == 0
    assert "delay_minutes" in result.output


def test_automation_group_lists_run_due():
    runner = CliRunner()
    result = runner.invoke(cli, ["automation", "--help"])
    assert result.exit_code == 0
    assert "run-due" in result.output
    assert "pending" in result.output
