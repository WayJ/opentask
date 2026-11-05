"""E67 CLI: version 1.60.0 + due/recurrence TZ help."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1510():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.60.0" in result.output
    assert VERSION == "1.60.0"
    assert __version__ == "1.60.0"


def test_run_due_reminders_help_mentions_workspace_tz():
    runner = CliRunner()
    result = runner.invoke(cli, ["notif", "run-due-reminders", "--help"])
    assert result.exit_code == 0
    assert "工作区时区" in result.output or "本地" in result.output


def test_recurrence_run_due_help_mentions_workspace_tz():
    runner = CliRunner()
    result = runner.invoke(cli, ["recurrence", "run-due", "--help"])
    assert result.exit_code == 0
    assert "工作区时区" in result.output or "时区" in result.output
