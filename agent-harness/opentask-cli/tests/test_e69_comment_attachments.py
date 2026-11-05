"""E69 CLI: issue comment attachment + version 1.56.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1530():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.56.0" in result.output
    assert VERSION == "1.56.0"
    assert __version__ == "1.56.0"


def test_comment_attachment_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "comment", "attachment", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "upload" in result.output
    assert "download" in result.output


def test_comment_attachment_list_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "comment", "attachment", "list", "--help"])
    assert result.exit_code == 0
    assert "ISSUE_ID" in result.output.upper() or "issue_id" in result.output.lower() or "COMMENT" in result.output.upper()
