"""E59 CLI: insights reports/digest + label-ids + version 1.48.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_pin_143():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.48.0" in result.output
    assert VERSION == "1.48.0"
    assert __version__ == "1.48.0"


def test_insights_summary_label_ids_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["insights", "summary", "--help"])
    assert result.exit_code == 0
    assert "--label-ids" in result.output
    assert "--label-id" in result.output


def test_insights_reports_and_digest_help():
    runner = CliRunner()
    for args in (
        ["insights", "reports", "--help"],
        ["insights", "reports", "list", "--help"],
        ["insights", "reports", "create", "--help"],
        ["insights", "reports", "delete", "--help"],
        ["insights", "run-digest", "--help"],
        ["insights", "export", "--help"],
    ):
        result = runner.invoke(cli, args)
        assert result.exit_code == 0, (args, result.output)
    create = runner.invoke(cli, ["insights", "reports", "create", "--help"])
    assert "--default" in create.output
    assert "--filters-json" in create.output
    export = runner.invoke(cli, ["insights", "export", "--help"])
    assert "--label-ids" in export.output
