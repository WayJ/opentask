"""E49 CLI: Display color scale/icon sets surface + version 1.78.0 (E93 adds display-prefs)."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import cli


def test_version_is_1_33_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.78.0" in result.output


def test_help_mentions_display_prefs_group():
    """E93: dedicated display-prefs get|set replaces the prior 'no subcommand' stance."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "display-prefs" in result.output
    group = runner.invoke(cli, ["display-prefs", "--help"])
    assert group.exit_code == 0
    assert "get" in group.output
    assert "set" in group.output


def test_init_version_pin():
    assert __version__ == "1.78.0"
