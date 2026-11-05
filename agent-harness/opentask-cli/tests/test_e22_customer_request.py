"""E22 CLI: customer / request surface + version 1.61.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_7_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.61.0" in result.output


def test_customer_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["customer", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output


def test_request_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["request", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
    assert "link-issue" in result.output
    assert "status-link" in result.output
    assert "public-status" in result.output
