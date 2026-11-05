"""E70 CLI: childProgress on issue show + version 1.54.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1540():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.54.0" in result.output
    assert VERSION == "1.54.0"
    assert __version__ == "1.54.0"


def test_issue_list_include_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "list", "--help"])
    assert result.exit_code == 0
    assert "include" in result.output.lower()
    assert "childProgress" in result.output or "childprogress" in result.output.lower()


def test_issue_show_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "show", "--help"])
    assert result.exit_code == 0
