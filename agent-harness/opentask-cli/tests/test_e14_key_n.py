"""E14: KEY-N detection still works for issue show."""
from __future__ import annotations

import re
from unittest import mock

import pytest
from click.testing import CliRunner

from opentask.opentask_cli import cli
from opentask.utils.api_client import OpenTaskClient


def test_key_n_pattern_examples():
    pat = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.I)
    assert pat.match("OT-1")
    assert pat.match("SMOKE2-12")
    assert pat.match("ISSUE2026-32")
    assert not pat.match("not-a-key")


def test_issue_show_uses_by_code_for_key(monkeypatch):
    runner = CliRunner()
    called = {}

    async def fake_get(self, issue_id, by_code=False):
        called["id"] = issue_id
        called["by_code"] = by_code
        return {"id": "uuid-1", "issue_code": "OT-1", "title": "t", "status": "open"}

    async def fake_comments(self, issue_id):
        return []

    monkeypatch.setattr(OpenTaskClient, "get_issue", fake_get)
    monkeypatch.setattr(OpenTaskClient, "get_comments", fake_comments)

    result = runner.invoke(cli, ["issue", "show", "OT-1", "--json"])
    assert result.exit_code == 0, result.output
    assert called.get("by_code") is True
    assert called.get("id") == "OT-1"
