"""E33 CLI: automation create|update CF + version 1.19.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_17_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.19.0" in result.output


def test_automation_help_has_update():
    runner = CliRunner()
    result = runner.invoke(cli, ["automation", "--help"])
    assert result.exit_code == 0
    assert "update" in result.output
    assert "create" in result.output


def test_automation_create_accepts_set_custom_field():
    runner = CliRunner()
    result = runner.invoke(cli, ["automation", "create", "--help"])
    assert result.exit_code == 0
    assert "set_custom_field" in result.output
    assert "--condition" in result.output
    assert "--action-config" in result.output


def test_automation_update_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["automation", "update", "--help"])
    assert result.exit_code == 0
    assert "--condition" in result.output
    assert "--action-config" in result.output
    assert "--clear-condition" in result.output
