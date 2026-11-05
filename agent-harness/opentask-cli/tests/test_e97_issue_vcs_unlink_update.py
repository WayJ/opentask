"""E97 CLI: issue unlink-vcs(+vcs-unlink) | update-vcs + version 1.81.0."""
from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli
from opentask.utils.api_client import OpenTaskClient

ROOT = Path(__file__).resolve().parents[1]

ISSUE_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
LINK_ID = "link-0001-1111-2222-333333333333"
ISSUE_CODE = "WAY-42"


def test_version_pins_1_81_0():
    assert __version__ == "1.81.0"
    assert VERSION == "1.81.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.81.0"
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'version = "1.81.0"' in pyproject
    setup = (ROOT / "setup.py").read_text()
    assert "1.81.0" in setup


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.81.0" in result.output


def test_api_client_delete_issue_vcs_link_still_present():
    assert hasattr(OpenTaskClient, "delete_issue_vcs_link")
    src = inspect.getsource(OpenTaskClient.delete_issue_vcs_link)
    assert "/vcs/links/" in src
    assert "self.delete" in src


def test_api_client_update_issue_vcs_link_exists():
    assert hasattr(OpenTaskClient, "update_issue_vcs_link")
    src = inspect.getsource(OpenTaskClient.update_issue_vcs_link)
    assert "/vcs/links/" in src
    assert "self.patch" in src


@pytest.mark.asyncio
async def test_api_client_update_issue_vcs_link_sends_camel_case():
    client = OpenTaskClient(base_url="http://example.test", token="t")
    with mock.patch.object(
        client, "patch", new=mock.AsyncMock(return_value={"id": LINK_ID, "status": "merged"})
    ) as p:
        await client.update_issue_vcs_link(
            ISSUE_ID,
            LINK_ID,
            status="merged",
            title="Done",
            prUrl="https://github.com/o/r/pull/1",
            branchName="feat/x",
            provider="github",
            externalId="42",
        )
        p.assert_awaited()
        args, kwargs = p.await_args
        assert args[0] == f"/api/issues/{ISSUE_ID}/vcs/links/{LINK_ID}"
        data = kwargs.get("data") or {}
        assert data["status"] == "merged"
        assert data["title"] == "Done"
        assert data["prUrl"] == "https://github.com/o/r/pull/1"
        assert data["branchName"] == "feat/x"
        assert data["provider"] == "github"
        assert data["externalId"] == "42"
        assert "pr_url" not in data
        assert "branch_name" not in data
        assert "external_id" not in data


def test_issue_help_lists_unlink_and_update_vcs():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "--help"])
    assert result.exit_code == 0
    assert "unlink-vcs" in result.output
    assert "update-vcs" in result.output


def test_unlink_vcs_help_and_alias():
    runner = CliRunner()
    primary = runner.invoke(cli, ["issue", "unlink-vcs", "--help"])
    assert primary.exit_code == 0
    assert "LINK" in primary.output.upper() or "link" in primary.output.lower()
    alias = runner.invoke(cli, ["issue", "vcs-unlink", "--help"])
    assert alias.exit_code == 0


def test_update_vcs_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "update-vcs", "--help"])
    assert result.exit_code == 0
    out = result.output.lower()
    for flag in ("--status", "--title", "--pr-url", "--branch-name", "--provider", "--external-id"):
        assert flag in out


def test_existing_vcs_commands_still_present():
    runner = CliRunner()
    for name in ("branch-name", "link-branch", "link-pr", "vcs-links"):
        r = runner.invoke(cli, ["issue", name, "--help"])
        assert r.exit_code == 0, name


def test_neighbor_helps_untouched():
    runner = CliRunner()
    at = runner.invoke(cli, ["access-token", "--help"])
    assert at.exit_code == 0
    assert "list" in at.output
    repo = runner.invoke(cli, ["project", "repo", "--help"])
    assert repo.exit_code == 0
    assert "list" in repo.output
    rx = runner.invoke(cli, ["issue", "reaction", "--help"])
    assert rx.exit_code == 0
    assert "list" in rx.output


def _patch_resolve(monkeypatch, real_id=ISSUE_ID):
    async def _resolve(client, issue_ref):
        return real_id, {"id": real_id, "issue_code": ISSUE_CODE}

    monkeypatch.setattr(
        "opentask.core.issue._resolve_issue_id",
        _resolve,
    )


def test_unlink_vcs_calls_delete_helper(monkeypatch):
    _patch_resolve(monkeypatch)
    calls = {}

    async def _delete(self, issue_id, link_id):
        calls["args"] = (issue_id, link_id)
        return {"id": link_id}

    monkeypatch.setattr(OpenTaskClient, "delete_issue_vcs_link", _delete)
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "unlink-vcs", ISSUE_CODE, LINK_ID])
    assert result.exit_code == 0, result.output
    assert calls["args"] == (ISSUE_ID, LINK_ID)
    assert LINK_ID in result.output or "unlink" in result.output.lower() or "Unlinked" in result.output


def test_vcs_unlink_alias_calls_delete(monkeypatch):
    _patch_resolve(monkeypatch)
    calls = {}

    async def _delete(self, issue_id, link_id):
        calls["args"] = (issue_id, link_id)
        return {"id": link_id}

    monkeypatch.setattr(OpenTaskClient, "delete_issue_vcs_link", _delete)
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "vcs-unlink", ISSUE_CODE, LINK_ID])
    assert result.exit_code == 0, result.output
    assert calls["args"] == (ISSUE_ID, LINK_ID)


def test_update_vcs_calls_helper_camel_case(monkeypatch):
    _patch_resolve(monkeypatch)
    calls = {}

    async def _update(self, issue_id, link_id, **kwargs):
        calls["args"] = (issue_id, link_id)
        calls["kwargs"] = kwargs
        return {
            "id": link_id,
            "kind": "pull_request",
            "status": "merged",
            "title": "Ship it",
            "prUrl": "https://github.com/o/r/pull/9",
            "branchName": None,
        }

    monkeypatch.setattr(OpenTaskClient, "update_issue_vcs_link", _update)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "issue",
            "update-vcs",
            ISSUE_CODE,
            LINK_ID,
            "--status",
            "merged",
            "--title",
            "Ship it",
            "--pr-url",
            "https://github.com/o/r/pull/9",
        ],
    )
    assert result.exit_code == 0, result.output
    assert calls["args"] == (ISSUE_ID, LINK_ID)
    assert calls["kwargs"]["status"] == "merged"
    assert calls["kwargs"]["title"] == "Ship it"
    assert calls["kwargs"]["prUrl"] == "https://github.com/o/r/pull/9"
    assert "pr_url" not in calls["kwargs"]
    assert LINK_ID in result.output or "merged" in result.output.lower()


def test_update_vcs_json_full(monkeypatch):
    _patch_resolve(monkeypatch)

    async def _update(self, issue_id, link_id, **kwargs):
        return {
            "id": link_id,
            "kind": "pull_request",
            "status": kwargs.get("status", "open"),
            "title": kwargs.get("title"),
            "prUrl": kwargs.get("prUrl"),
            "provider": "github",
        }

    monkeypatch.setattr(OpenTaskClient, "update_issue_vcs_link", _update)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "issue",
            "update-vcs",
            ISSUE_CODE,
            LINK_ID,
            "--status",
            "closed",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload.get("success") is True
    data = payload.get("data") or {}
    assert data.get("id") == LINK_ID
    assert data.get("status") == "closed"


def test_empty_update_vcs_rejected_without_api_call(monkeypatch):
    _patch_resolve(monkeypatch)
    called = {"n": 0}

    async def _update(self, issue_id, link_id, **kwargs):
        called["n"] += 1
        return {}

    monkeypatch.setattr(OpenTaskClient, "update_issue_vcs_link", _update)
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "update-vcs", ISSUE_CODE, LINK_ID])
    assert result.exit_code != 0
    assert called["n"] == 0
    assert (
        "at least one" in result.output.lower()
        or "provide" in result.output.lower()
        or "specify" in result.output.lower()
    )


def test_unlink_vcs_json(monkeypatch):
    _patch_resolve(monkeypatch)

    async def _delete(self, issue_id, link_id):
        return {"id": link_id}

    monkeypatch.setattr(OpenTaskClient, "delete_issue_vcs_link", _delete)
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "unlink-vcs", ISSUE_CODE, LINK_ID, "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload.get("success") is True
    data = payload.get("data") or {}
    assert data.get("id") == LINK_ID
