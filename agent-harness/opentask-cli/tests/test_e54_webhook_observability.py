"""E54 CLI: webhook stats|dead-letter + version 1.59.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1_39_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.59.0" in result.output
    assert VERSION == "1.59.0"
    assert __version__ == "1.59.0"


def test_webhook_stats_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "stats", "--help"])
    assert result.exit_code == 0
    assert "--webhook-id" in result.output
    assert "--window" in result.output
    assert "--json" in result.output


def test_webhook_dead_letter_group_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "dead-letter", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "retry" in result.output


def test_webhook_dead_letter_list_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "dead-letter", "list", "--help"])
    assert result.exit_code == 0
    assert "--webhook-id" in result.output
    assert "--event" in result.output


def test_webhook_dead_letter_retry_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "dead-letter", "retry", "--help"])
    assert result.exit_code == 0
    assert "--id" in result.output
    assert "--ids" in result.output
