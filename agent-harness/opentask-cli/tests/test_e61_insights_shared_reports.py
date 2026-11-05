"""E61 CLI: insights shared reports + version 1.74.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_is_1_45_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.74.0" in result.output
    assert VERSION == "1.74.0"
    assert __version__ == "1.74.0"


def test_insights_reports_shared_help():
    runner = CliRunner()
    for args in (
        ["insights", "reports", "--help"],
        ["insights", "reports", "list", "--help"],
        ["insights", "reports", "create", "--help"],
        ["insights", "reports", "set-visibility", "--help"],
        ["insights", "reports", "fork", "--help"],
        ["insights", "reports", "delete", "--help"],
    ):
        result = runner.invoke(cli, args)
        assert result.exit_code == 0, (args, result.output)

    list_help = runner.invoke(cli, ["insights", "reports", "list", "--help"])
    assert "--mine" in list_help.output
    assert "--shared" in list_help.output
    assert "--all" in list_help.output

    create = runner.invoke(cli, ["insights", "reports", "create", "--help"])
    assert "--visibility" in create.output

    fork = runner.invoke(cli, ["insights", "reports", "fork", "--help"])
    assert "REPORT_ID" in fork.output or "report_id" in fork.output.lower()
