"""E25 CLI: custom-field list|create + issue set-field + version 1.42.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_9_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.42.0" in result.output


def test_custom_field_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["custom-field", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output


def test_custom_field_create_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["custom-field", "create", "--help"])
    assert result.exit_code == 0
    assert "--type" in result.output
    assert "--name" in result.output


def test_issue_set_field_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "set-field", "--help"])
    assert result.exit_code == 0
    assert "KEY" in result.output.upper() or "key" in result.output
