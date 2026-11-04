"""E51 CLI: webhook events + pack enums + version 1.42.0."""
from click.testing import CliRunner

from opentask.core.webhook import EVENTS
from opentask.opentask_cli import cli


def test_version_1_35_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.42.0" in result.output


def test_events_include_e51_pack():
    for ev in (
        "issue.cycle_changed",
        "issue.estimate_changed",
        "issue.project_changed",
        "issue.sla_paused",
        "issue.sla_resumed",
    ):
        assert ev in EVENTS


def test_webhook_events_subcommand():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "events"])
    assert result.exit_code == 0
    assert "issue.cycle_changed" in result.output
    assert "issue.sla_resumed" in result.output


def test_webhook_events_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "events", "--json"])
    assert result.exit_code == 0
    assert "issue.project_changed" in result.output


def test_webhook_help_lists_events_cmd():
    runner = CliRunner()
    result = runner.invoke(cli, ["webhook", "--help"])
    assert result.exit_code == 0
    assert "events" in result.output
