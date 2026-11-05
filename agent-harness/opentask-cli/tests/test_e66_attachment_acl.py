"""E66 CLI: issue attachment download|signed-url + version 1.57.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1_50_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.57.0" in result.output
    assert VERSION == "1.57.0"
    assert __version__ == "1.57.0"


def test_issue_attachment_help():
    runner = CliRunner()
    help_out = runner.invoke(cli, ["issue", "attachment", "--help"]).output
    assert "download" in help_out
    assert "signed-url" in help_out
    dl = runner.invoke(cli, ["issue", "attachment", "download", "--help"])
    assert dl.exit_code == 0
    assert "--out" in dl.output
    sig = runner.invoke(cli, ["issue", "attachment", "signed-url", "--help"])
    assert sig.exit_code == 0
    assert "--purpose" in sig.output
