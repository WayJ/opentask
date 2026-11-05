"""E39 CLI: notif run-due-reminders + prefs due_reminder keys + version 1.66.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_23_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.66.0" in result.output


def test_run_due_reminders_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["notif", "run-due-reminders", "--help"])
    assert result.exit_code == 0
    assert "run-due-reminders" in result.output
    assert "cron" in result.output.lower() or "UTC" in result.output or "到期" in result.output


def test_due_deliveries_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["notif", "due-deliveries", "--help"])
    assert result.exit_code == 0


def test_prefs_set_accepts_due_reminder_keys():
    runner = CliRunner()
    result = runner.invoke(cli, ["notif", "prefs", "set", "--help"])
    assert result.exit_code == 0
    assert "due_reminder" in result.output
    assert "due_reminder_digest" in result.output
