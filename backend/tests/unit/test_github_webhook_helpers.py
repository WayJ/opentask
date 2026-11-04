"""E11-S2: GitHub PR webhook helpers."""
from __future__ import annotations

import hashlib
import hmac

from opentask.services.vcs.github_webhook import (
    map_github_pr_status,
    verify_github_signature,
)


def test_map_status_merged():
    assert map_github_pr_status(state="closed", merged=True, draft=False) == "merged"


def test_map_status_draft():
    assert map_github_pr_status(state="open", merged=False, draft=True) == "draft"


def test_map_status_open_closed():
    assert map_github_pr_status(state="open", merged=False, draft=False) == "open"
    assert map_github_pr_status(state="closed", merged=False, draft=False) == "closed"


def test_verify_signature_ok():
    body = b'{"action":"opened"}'
    secret = "testsecret"
    dig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_github_signature(body, f"sha256={dig}", secret) is True


def test_verify_signature_bad():
    assert verify_github_signature(b"{}", "sha256=dead", "secret") is False


def test_verify_skip_when_secret_empty():
    assert verify_github_signature(b"{}", None, "") is True
    assert verify_github_signature(b"{}", "sha256=x", "") is True
