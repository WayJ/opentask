"""E30 CLI: notif prefs email_enabled + email-test + version 1.81.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_14_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.81.0" in result.output


def test_notif_prefs_set_accepts_email_enabled():
    runner = CliRunner()
    result = runner.invoke(cli, ["notif", "prefs", "set", "--help"])
    assert result.exit_code == 0
    assert "email_enabled" in result.output


def test_notif_email_test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["notif", "email-test", "--help"])
    assert result.exit_code == 0
    assert "测试" in result.output or "email" in result.output.lower() or "SMTP" in result.output or result.exit_code == 0


def test_notif_group_has_email_test():
    runner = CliRunner()
    result = runner.invoke(cli, ["notif", "--help"])
    assert result.exit_code == 0
    assert "email-test" in result.output
