"""E76 CLI: issue link list|add|rm + version 1.69.0."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_60_0():
    assert __version__ == "1.69.0"
    assert VERSION == "1.69.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.69.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.69.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.69.0" in setup


def test_issue_link_group_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "link", "--help"])
    assert result.exit_code == 0, result.output
    assert "list" in result.output
    assert "add" in result.output
    assert "rm" in result.output


def test_issue_link_add_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "link", "add", "--help"])
    assert result.exit_code == 0, result.output
    assert "--title" in result.output
    assert "--json" in result.output


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.69.0" in result.output
