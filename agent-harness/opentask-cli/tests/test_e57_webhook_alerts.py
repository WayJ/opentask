"""E57 CLI: webhook alerts|run-alert-eval + version 1.74.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1_42_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.75.0" in result.output
    assert VERSION == "1.75.0"
    assert __version__ == "1.75.0"


def test_webhook_alerts_group_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "alerts", "--help"])
    assert result.exit_code == 0
    assert "show" in result.output
    assert "set" in result.output
    assert "mute" in result.output
    assert "unmute" in result.output


def test_webhook_alerts_show_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "alerts", "show", "--help"])
    assert result.exit_code == 0
    assert "--webhook-id" in result.output


def test_webhook_alerts_set_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "alerts", "set", "--help"])
    assert result.exit_code == 0
    assert "--enabled" in result.output or "--disabled" in result.output
    assert "--window-hours" in result.output
    assert "--dead-threshold" in result.output
    assert "--auto-disable" in result.output


def test_webhook_alerts_mute_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "alerts", "mute", "--help"])
    assert result.exit_code == 0
    assert "--until" in result.output


def test_webhook_run_alert_eval_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "run-alert-eval", "--help"])
    assert result.exit_code == 0
    assert "alert" in result.output.lower()
