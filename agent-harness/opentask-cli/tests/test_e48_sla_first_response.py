"""E48 CLI: sla --metric first_response + version 1.69.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_32_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.69.0" in result.output


def test_sla_policy_create_help_has_metric_first_response():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "policy", "create", "--help"])
    assert result.exit_code == 0
    assert "--metric" in result.output
    assert "first_response" in result.output


def test_sla_policy_update_help_has_metric():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "policy", "update", "--help"])
    assert result.exit_code == 0
    assert "--metric" in result.output
