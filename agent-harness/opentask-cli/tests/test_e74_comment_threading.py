"""E74: CLI 1.72.0 pins + comment --parent-id."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_58_0():
    assert __version__ == "1.72.0"
    assert VERSION == "1.72.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.72.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.72.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.72.0" in setup


def test_comment_add_help_has_parent_id():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "comment", "add", "--help"])
    assert result.exit_code == 0
    assert "--parent-id" in result.output
