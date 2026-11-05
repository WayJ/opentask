"""E77 CLI: issue trash|restore + version 1.66.0."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_61_0():
    assert __version__ == "1.66.0"
    assert VERSION == "1.66.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.66.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.66.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.66.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.66.0" in result.output


def test_issue_trash_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "trash", "--help"])
    assert result.exit_code == 0, result.output
    assert "--json" in result.output
    assert "--limit" in result.output


def test_issue_restore_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "restore", "--help"])
    assert result.exit_code == 0, result.output
    assert "--json" in result.output
    assert "ISSUE_ID" in result.output or "issue_id" in result.output.lower()


def test_issue_delete_still_rejected():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "delete", "WAY-1"])
    assert result.exit_code != 0
    assert "Cannot delete" in result.output or "CLI_DELETE" in result.output or "not allowed" in result.output.lower()
