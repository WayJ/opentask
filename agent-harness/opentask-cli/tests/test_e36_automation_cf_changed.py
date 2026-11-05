"""E36 CLI: automation custom_field_changed + version 1.65.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_20_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.65.0" in result.output


def test_automation_create_accepts_custom_field_changed():
    runner = CliRunner()
    result = runner.invoke(cli, ["automation", "create", "--help"])
    assert result.exit_code == 0
    assert "custom_field_changed" in result.output
    assert "field_key" in result.output or "cf-changed" in result.output
    assert "customFields" in result.output or "customField" in result.output
