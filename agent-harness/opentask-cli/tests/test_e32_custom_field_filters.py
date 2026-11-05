"""E32 CLI: issue list --cf + version 1.80.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_16_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.80.0" in result.output


def test_issue_list_accepts_cf_option():
    runner = CliRunner()
    # Help should mention --cf
    result = runner.invoke(cli, ["issue", "list", "--help"])
    assert result.exit_code == 0
    assert "--cf" in result.output
