"""E41 CLI: issue timeline|timeline-export|timeline-export-workspace + version 1.40.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli
from opentask.core.webhook import EVENTS


def test_version_1_25_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.40.0" in result.output


def test_issue_timeline_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "timeline", "--help"])
    assert result.exit_code == 0
    assert "timeline" in result.output.lower()


def test_issue_timeline_export_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "timeline-export", "--help"])
    assert result.exit_code == 0
    assert "--out" in result.output
    assert "--action-type" in result.output


def test_issue_timeline_export_workspace_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "timeline-export-workspace", "--help"])
    assert result.exit_code == 0
    assert "--since" in result.output
    assert "--out" in result.output


def test_webhook_events_include_custom_field_changed():
    assert "issue.custom_field_changed" in EVENTS
