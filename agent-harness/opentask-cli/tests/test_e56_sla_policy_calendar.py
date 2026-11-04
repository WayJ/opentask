"""E56 CLI: sla policy --calendar-json|--clear-calendar + version 1.41.0."""
from click.testing import CliRunner
from opentask.opentask_cli import cli, VERSION


def test_version_pin():
    assert VERSION == "1.41.0"
    r = CliRunner().invoke(cli, ["--version"])
    assert "1.41.0" in r.output


def test_policy_create_help_shows_calendar_json():
    r = CliRunner().invoke(cli, ["sla", "policy", "create", "--help"])
    assert r.exit_code == 0
    assert "--calendar-json" in r.output


def test_policy_update_help_shows_calendar_flags():
    r = CliRunner().invoke(cli, ["sla", "policy", "update", "--help"])
    assert r.exit_code == 0
    assert "--calendar-json" in r.output
    assert "--clear-calendar" in r.output
