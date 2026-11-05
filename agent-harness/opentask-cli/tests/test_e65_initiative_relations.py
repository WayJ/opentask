"""E65 CLI: initiative relations + version 1.74.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1_50_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.74.0" in result.output
    assert VERSION == "1.74.0"
    assert __version__ == "1.74.0"


def test_initiative_relations_help():
    runner = CliRunner()
    help_out = runner.invoke(cli, ["initiative", "--help"]).output
    assert "relations" in help_out
    assert "relation" in help_out
    add_help = runner.invoke(cli, ["initiative", "relation", "add", "--help"]).output
    assert "--target" in add_help
    assert "--type" in add_help
    rm_help = runner.invoke(cli, ["initiative", "relation", "remove", "--help"]).output
    assert "--relation-id" in rm_help


def test_initiative_relations_list_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["initiative", "relations", "list", "--help"])
    assert result.exit_code == 0
    assert "INITIATIVE_ID" in result.output or "initiative_id" in result.output.lower()
