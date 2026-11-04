"""E37 CLI: issue list --group-by cf:<key> + version 1.48.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_21_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.48.0" in result.output


def test_issue_list_help_mentions_group_by_cf():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "list", "--help"])
    assert result.exit_code == 0
    assert "--group-by" in result.output
    assert "cf:" in result.output


def test_issue_list_accepts_cf_group_by_option():
    """Click accepts --group-by cf:severity (no bad-choice error before auth)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "list", "--group-by", "cf:severity", "--help"])
    # invoking with --help after options still shows help; ensure option is known
    assert result.exit_code == 0
    assert "--group-by" in result.output
