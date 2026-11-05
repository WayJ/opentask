"""E27 CLI: notif prefs get|set + version 1.52.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_11_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.52.0" in result.output


def test_notif_prefs_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["notif", "prefs", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "set" in result.output


def test_notif_prefs_set_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["notif", "prefs", "set", "--help"])
    assert result.exit_code == 0
    assert "--key" in result.output
    assert "--on" in result.output or "--off" in result.output
