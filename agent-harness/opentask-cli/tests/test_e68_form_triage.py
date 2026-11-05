"""E68 CLI: form --enqueue-triage + version 1.69.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1520():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.69.0" in result.output
    assert VERSION == "1.69.0"
    assert __version__ == "1.69.0"


def test_form_create_help_enqueue_triage():
    runner = CliRunner()
    result = runner.invoke(cli, ["form", "create", "--help"])
    assert result.exit_code == 0
    assert "--enqueue-triage" in result.output


def test_form_update_help_enqueue_triage():
    runner = CliRunner()
    result = runner.invoke(cli, ["form", "update", "--help"])
    assert result.exit_code == 0
    assert "--enqueue-triage" in result.output
