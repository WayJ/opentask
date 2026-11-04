"""E20: issue bulk-update command surface"""
from click.testing import CliRunner
from opentask.opentask_cli import cli


def test_bulk_update_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "bulk-update", "--help"])
    assert result.exit_code == 0
    assert "bulk-update" in result.output.lower() or "Bulk update" in result.output
    assert "--status" in result.output
    assert "--cycle-id" in result.output
    assert "--tag-ids" in result.output


def test_version_is_1_6_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.44.0" in result.output
