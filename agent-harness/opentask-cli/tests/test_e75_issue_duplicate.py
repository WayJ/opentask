"""E75 CLI: issue duplicate + version 1.80.0."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_60_0():
    assert __version__ == "1.80.0"
    assert VERSION == "1.80.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.80.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.80.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.80.0" in setup


def test_issue_duplicate_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "duplicate", "--help"])
    assert result.exit_code == 0, result.output
    assert "--title" in result.output
    assert "--json" in result.output
    assert "ISSUE_ID" in result.output or "issue_id" in result.output.lower()


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.80.0" in result.output
