"""E45 CLI: sla --pause + automation issue.sla_breached + version 1.59.0."""
from click.testing import CliRunner

from opentask.opentask_cli import cli
from opentask.core.automation import TRIGGERS


def test_version_1_29_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.59.0" in result.output


def test_sla_policy_create_help_has_pause():
    runner = CliRunner()
    result = runner.invoke(cli, ["sla", "policy", "create", "--help"])
    assert result.exit_code == 0
    assert "--pause" in result.output


def test_automation_triggers_include_sla_breached():
    assert "issue.sla_breached" in TRIGGERS
