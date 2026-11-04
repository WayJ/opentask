"""E50 CLI: workspace/sla business-hours + version 1.39.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_34_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.39.0" in result.output


def test_workspace_update_help_has_business_hours():
    runner = CliRunner()
    result = runner.invoke(cli, ["workspace", "update", "--help"])
    assert result.exit_code == 0
    assert "--timezone" in result.output
    assert "business-hours" in result.output


def test_sla_business_hours_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "business-hours", "--help"])
    assert result.exit_code == 0
    assert "show" in result.output
    assert "set" in result.output


def test_sla_business_hours_set_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "business-hours", "set", "--help"])
    assert result.exit_code == 0
    assert "--timezone" in result.output
    assert "--windows-json" in result.output
