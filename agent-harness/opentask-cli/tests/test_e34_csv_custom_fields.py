"""E34 CLI: issue export|import cf.* + version 1.62.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_18_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.62.0" in result.output


def test_issue_export_help_mentions_cf():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "export", "--help"])
    assert result.exit_code == 0
    assert "cf." in result.output


def test_issue_import_help_mentions_cf():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "import", "--help"])
    assert result.exit_code == 0
    assert "cf." in result.output
