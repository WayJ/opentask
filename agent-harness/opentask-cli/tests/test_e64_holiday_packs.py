"""E64 CLI: sla holiday-packs list --region/--year + version 1.75.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1_50_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.75.0" in result.output
    assert VERSION == "1.75.0"
    assert __version__ == "1.75.0"


def test_holiday_packs_list_help_region_year():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "holiday-packs", "list", "--help"])
    assert result.exit_code == 0
    assert "--region" in result.output
    assert "--year" in result.output
