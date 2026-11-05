"""E82 CLI: issue-template CRUD+seed + issue create --template-id + version 1.68.0."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli

ROOT = Path(__file__).resolve().parents[1]


def test_version_pins_1_66_0():
    assert __version__ == "1.68.0"
    assert VERSION == "1.68.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.68.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.68.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.68.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.68.0" in result.output


def test_issue_template_group_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue-template", "--help"])
    assert result.exit_code == 0, result.output
    for name in ("list", "show", "create", "update", "delete", "seed"):
        assert name in result.output


def test_issue_create_help_has_template_id():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "create", "--help"])
    assert result.exit_code == 0
    assert "--template-id" in result.output


def test_issue_template_list_show_create_update_delete_seed():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.list_issue_templates = AsyncMock(
        return_value={
            "rows": [
                {
                    "id": "tpl-1",
                    "name": "Bug",
                    "source": "seed",
                    "payload": {"type": "bug"},
                }
            ],
            "total": 1,
        }
    )
    mock_client.get_issue_template = AsyncMock(
        return_value={
            "id": "tpl-1",
            "name": "Bug",
            "description": "d",
            "source": "seed",
            "payload": {"type": "bug", "priority": "high"},
        }
    )
    mock_client.create_issue_template = AsyncMock(
        return_value={"id": "tpl-2", "name": "Custom", "source": "custom"}
    )
    mock_client.update_issue_template = AsyncMock(
        return_value={"id": "tpl-2", "name": "Custom2", "source": "custom"}
    )
    mock_client.delete_issue_template = AsyncMock(return_value={"id": "tpl-2"})
    mock_client.seed_issue_templates = AsyncMock(
        return_value={"rows": [{"id": "tpl-1", "seedKey": "bug_report"}], "total": 5}
    )

    with patch("opentask.core.issue_template.OpenTaskClient", return_value=mock_client):
        r_list = runner.invoke(cli, ["issue-template", "list", "--json"])
        r_show = runner.invoke(cli, ["issue-template", "show", "tpl-1", "--json"])
        r_create = runner.invoke(
            cli,
            [
                "issue-template",
                "create",
                "--name",
                "Custom",
                "--payload-json",
                '{"type":"feature"}',
                "--sort-order",
                "2",
                "--json",
            ],
        )
        r_update = runner.invoke(
            cli,
            ["issue-template", "update", "tpl-2", "--name", "Custom2", "--json"],
        )
        r_delete = runner.invoke(cli, ["issue-template", "delete", "tpl-2", "--json"])
        r_seed = runner.invoke(cli, ["issue-template", "seed", "--json"])

    assert r_list.exit_code == 0, r_list.output
    assert r_show.exit_code == 0, r_show.output
    assert r_create.exit_code == 0, r_create.output
    assert r_update.exit_code == 0, r_update.output
    assert r_delete.exit_code == 0, r_delete.output
    assert r_seed.exit_code == 0, r_seed.output

    mock_client.list_issue_templates.assert_awaited()
    mock_client.get_issue_template.assert_awaited_with("tpl-1")
    mock_client.create_issue_template.assert_awaited()
    kwargs = mock_client.create_issue_template.await_args.kwargs
    assert kwargs["name"] == "Custom"
    assert kwargs["payload"] == {"type": "feature"}
    assert kwargs["sort_order"] == 2
    mock_client.update_issue_template.assert_awaited()
    mock_client.delete_issue_template.assert_awaited_with("tpl-2")
    mock_client.seed_issue_templates.assert_awaited()

    seed_payload = json.loads(r_seed.output)
    assert seed_payload.get("success") is True or "bug_report" in r_seed.output


def test_issue_create_passes_template_id():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.create_issue = AsyncMock(
        return_value={
            "id": "iss-1",
            "issue_code": "OT-1",
            "title": "Login crash",
            "type": "bug",
        }
    )
    with patch("opentask.core.issue.OpenTaskClient", return_value=mock_client):
        result = runner.invoke(
            cli,
            [
                "issue",
                "create",
                "-t",
                "Login crash",
                "--template-id",
                "tpl-1",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.output
    mock_client.create_issue.assert_awaited()
    kwargs = mock_client.create_issue.await_args.kwargs
    assert kwargs.get("template_id") == "tpl-1"
