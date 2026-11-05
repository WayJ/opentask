"""E28 CLI: issue export|import + version 1.64.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_12_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.64.0" in result.output


def test_issue_export_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "export", "--help"])
    assert result.exit_code == 0
    assert "--out" in result.output


def test_issue_import_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "import", "--help"])
    assert result.exit_code == 0
    assert "FILE" in result.output.upper() or "file" in result.output
