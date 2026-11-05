"""E72 CLI: project-template + project create --template-id + version 1.60.0."""
from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_pins_1_56_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.60.0" in result.output
    assert VERSION == "1.60.0"
    assert __version__ == "1.60.0"
    version_file = Path(__file__).resolve().parents[1] / "VERSION"
    assert version_file.read_text().strip() == "1.60.0"


def test_project_template_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["project-template", "--help"])
    assert result.exit_code == 0
    for cmd in ("list", "show", "create", "update", "delete", "apply", "from-project"):
        assert cmd in result.output


def test_project_create_help_has_template_id():
    runner = CliRunner()
    result = runner.invoke(cli, ["project", "create", "--help"])
    assert result.exit_code == 0
    assert "--template-id" in result.output


def test_project_template_apply_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["project-template", "apply", "--help"])
    assert result.exit_code == 0
    assert "--id" in result.output
    assert "--name" in result.output
