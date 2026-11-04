"""E11-S1: CLI branch-name / link-branch — same HTTP contract."""
from __future__ import annotations

from unittest import mock

import pytest
from click.testing import CliRunner

from opentask.opentask_cli import cli
from opentask.utils.api_client import OpenTaskClient


def test_issue_branch_name_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "branch-name", "--help"])
    assert result.exit_code == 0
    assert "branch" in result.output.lower()


def test_issue_link_branch_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["issue", "link-branch", "--help"])
    assert result.exit_code == 0
    assert "link" in result.output.lower()


@pytest.mark.asyncio
async def test_api_client_vcs_paths():
    client = OpenTaskClient(base_url="http://example.test", token="t")
    with mock.patch.object(client, "get", new=mock.AsyncMock(return_value={"branchName": "A-1-x"})) as g:
        data = await client.get_issue_branch_name("uuid-1")
        assert data["branchName"] == "A-1-x"
        g.assert_awaited_with("/api/issues/uuid-1/vcs/branch-name")
    with mock.patch.object(client, "post", new=mock.AsyncMock(return_value={"id": "l1"})) as p:
        await client.create_issue_vcs_link("uuid-1", kind="branch", branchName="A-1-x")
        p.assert_awaited()
        args, kwargs = p.await_args
        assert args[0] == "/api/issues/uuid-1/vcs/links"
        assert kwargs.get("data", args[1] if len(args) > 1 else None) is not None or "data" in kwargs
        # post(endpoint, data=kwargs)
        assert kwargs["data"]["kind"] == "branch"
        assert kwargs["data"]["branchName"] == "A-1-x"
