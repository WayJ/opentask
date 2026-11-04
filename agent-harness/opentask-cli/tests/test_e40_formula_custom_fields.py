"""E40 CLI: custom-field formula create/update/validate-formula + version 1.30.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_24_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.30.0" in result.output


def test_custom_field_create_help_formula():
    runner = CliRunner()
    result = runner.invoke(cli, ["custom-field", "create", "--help"])
    assert result.exit_code == 0
    assert "formula" in result.output
    assert "--expr" in result.output
    assert "IF" in result.output or "COALESCE" in result.output


def test_validate_formula_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["custom-field", "validate-formula", "--help"])
    assert result.exit_code == 0
    assert "--expr" in result.output


def test_custom_field_update_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["custom-field", "update", "--help"])
    assert result.exit_code == 0
    assert "--expr" in result.output
