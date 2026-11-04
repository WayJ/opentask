"""E35 CLI: recurrence list|create|update|delete|run-due + version 1.30.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_19_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.30.0" in result.output


def test_recurrence_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["recurrence", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
    assert "update" in result.output
    assert "delete" in result.output
    assert "run-due" in result.output


def test_recurrence_create_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["recurrence", "create", "--help"])
    assert result.exit_code == 0
    assert "--title-template" in result.output
    assert "--interval" in result.output
    assert "--next-run-at" in result.output
