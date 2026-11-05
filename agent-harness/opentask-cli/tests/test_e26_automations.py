"""E26 CLI: automation list|create|enable|disable + version 1.54.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_10_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.54.0" in result.output


def test_automation_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["automation", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
    assert "enable" in result.output
    assert "disable" in result.output
    assert "update" in result.output


def test_automation_create_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["automation", "create", "--help"])
    assert result.exit_code == 0
    assert "--trigger" in result.output
    assert "--action" in result.output
