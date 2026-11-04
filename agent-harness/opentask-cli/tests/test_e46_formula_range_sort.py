"""E46 CLI: formula range/sort surfaces + version 1.48.0."""
from click.testing import CliRunner
from opentask.opentask_cli import cli


def test_version_1_30_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.48.0" in result.output


def test_issue_list_help_mentions_range_and_cf_sort():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "list", "--help"])
    assert result.exit_code == 0
    assert "--cf" in result.output
    assert "gte" in result.output.lower() or "[gte]" in result.output
    assert "cf:" in result.output or "Sort field" in result.output
