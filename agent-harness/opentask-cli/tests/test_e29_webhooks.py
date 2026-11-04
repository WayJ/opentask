"""E29 CLI: webhook list|create|update|delete|test + version 1.23.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_13_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.23.0" in result.output


def test_webhook_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
    assert "update" in result.output
    assert "delete" in result.output
    assert "test" in result.output


def test_webhook_create_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "create", "--help"])
    assert result.exit_code == 0
    assert "--url" in result.output
    assert "--events" in result.output
