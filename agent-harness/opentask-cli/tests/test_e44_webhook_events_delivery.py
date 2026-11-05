"""E44 CLI: webhook deliveries|retry|run-due + version 1.67.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_28_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.67.0" in result.output


def test_webhook_help_includes_e44():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "--help"])
    assert result.exit_code == 0
    assert "deliveries" in result.output
    assert "retry" in result.output
    assert "run-due" in result.output


def test_webhook_create_help_lists_new_events():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "create", "--help"])
    assert result.exit_code == 0
    # help mentions events option; EVENTS validated at runtime
    assert "--events" in result.output


def test_webhook_deliveries_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "deliveries", "--help"])
    assert result.exit_code == 0
    assert "--status" in result.output
