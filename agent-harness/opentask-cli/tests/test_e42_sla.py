"""E42 CLI: sla policy|issue|run-due + version 1.41.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_version_1_26_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.41.0" in result.output


def test_sla_run_due_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "run-due", "--help"])
    assert result.exit_code == 0
    assert "run-due" in result.output
    assert "cron" in result.output.lower() or "UTC" in result.output


def test_sla_policy_create_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "policy", "create", "--help"])
    assert result.exit_code == 0
    assert "--start" in result.output
    assert "--minutes" in result.output


def test_sla_issue_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "issue", "--help"])
    assert result.exit_code == 0


def test_sla_policy_list_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "policy", "list", "--help"])
    assert result.exit_code == 0


def test_webhook_events_include_sla_breached():
    from opentask.core.webhook import EVENTS
    assert "issue.sla_breached" in EVENTS
