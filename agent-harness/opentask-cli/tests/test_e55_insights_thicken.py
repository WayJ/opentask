"""E55 CLI: insights summary filters + export + version 1.45.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1_39_0_pins():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.45.0" in result.output
    assert VERSION == "1.45.0"
    assert __version__ == "1.45.0"


def test_insights_export_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["insights", "export", "--help"])
    assert result.exit_code == 0
    assert "--project-id" in result.output
    assert "--label-id" in result.output
    assert "--cycle" in result.output
    assert "-o" in result.output or "--output" in result.output


def test_insights_summary_filter_flags():
    runner = CliRunner()
    result = runner.invoke(cli, ["insights", "summary", "--help"])
    assert result.exit_code == 0
    assert "--project-id" in result.output
    assert "--label-id" in result.output
    assert "--cycle" in result.output
    assert "--json" in result.output
