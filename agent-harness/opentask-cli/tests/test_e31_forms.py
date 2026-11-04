"""E31 CLI: form list|create|update|delete|url + version 1.51.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_15_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.51.0" in result.output


def test_form_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["form", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
    assert "update" in result.output
    assert "delete" in result.output
    assert "url" in result.output


def test_form_create_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["form", "create", "--help"])
    assert result.exit_code == 0
    assert "--name" in result.output
    assert "--fields-json" in result.output
