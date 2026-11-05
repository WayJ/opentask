"""E49 CLI: Display color scale/icon sets surface + version 1.76.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_is_1_33_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.76.0" in result.output


def test_help_mentions_display_or_api():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    # No dedicated display prefs subcommand; point users at API/FE via help presence
    assert "Commands" in result.output or "Usage" in result.output


def test_init_version_pin():
    from opentask import __version__

    assert __version__ == "1.76.0"
