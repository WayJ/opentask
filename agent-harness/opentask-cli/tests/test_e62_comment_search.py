"""E62 CLI: comments search output + version 1.77.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_pin_146():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.77.0" in result.output
    assert VERSION == "1.77.0"
    assert __version__ == "1.77.0"


def test_search_help_mentions_limit():
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--help"])
    assert result.exit_code == 0, result.output
    assert "limit" in result.output
