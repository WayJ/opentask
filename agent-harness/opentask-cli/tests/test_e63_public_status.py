"""E63 CLI: request status-link + public-status + version 1.48.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1_47_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.48.0" in result.output
    assert VERSION == "1.48.0"
    assert __version__ == "1.48.0"


def test_request_status_link_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["request", "status-link", "--help"])
    assert result.exit_code == 0
    assert "enable" in result.output
    assert "rotate" in result.output
    assert "revoke" in result.output
    assert "show" in result.output


def test_request_public_status_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["request", "public-status", "--help"])
    assert result.exit_code == 0
    assert "TOKEN" in result.output or "token" in result.output.lower()


def test_request_help_lists_new_commands():
    runner = CliRunner()
    result = runner.invoke(cli, ["request", "--help"])
    assert result.exit_code == 0
    assert "status-link" in result.output
    assert "public-status" in result.output
