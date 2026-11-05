"""E58 CLI: sla holiday-packs + version 1.76.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1_42_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.76.0" in result.output
    assert VERSION == "1.76.0"
    assert __version__ == "1.76.0"


def test_holiday_packs_group_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "holiday-packs", "--help"])
    assert result.exit_code == 0
    for sub in ("list", "show", "preview", "apply"):
        assert sub in result.output


def test_holiday_packs_show_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "holiday-packs", "show", "--help"])
    assert result.exit_code == 0
    assert "--region" in result.output
    assert "--year" in result.output


def test_holiday_packs_apply_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "holiday-packs", "apply", "--help"])
    assert result.exit_code == 0
    assert "--policy-id" in result.output
    assert "--yes" in result.output
