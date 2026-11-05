"""E71 CLI: issue --assignees + show Assignees + version 1.75.0."""
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_pins_1_55_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.75.0" in result.output
    assert VERSION == "1.75.0"
    assert __version__ == "1.75.0"
    version_file = Path(__file__).resolve().parents[1] / "VERSION"
    assert version_file.read_text().strip() == "1.75.0"


def test_create_help_has_assignees():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "create", "--help"])
    assert result.exit_code == 0
    assert "--assignees" in result.output


def test_update_help_has_assignees():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "update", "--help"])
    assert result.exit_code == 0
    assert "--assignees" in result.output
