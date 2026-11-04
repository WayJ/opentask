"""E43 CLI: formula cf filter surfaces + version 1.35.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_27_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.35.0" in result.output


def test_issue_list_cf_help_mentions_custom_fields():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "list", "--help"])
    assert result.exit_code == 0
    # --cf option exists (formula keys share same contract)
    assert "--cf" in result.output or "cf" in result.output.lower()
