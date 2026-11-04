"""GitHub-compatible PR webhook helpers (E11-S2). Local-dev: empty secret skips verify."""
from __future__ import annotations

import hashlib
import hmac
from typing import Any, Optional


def map_github_pr_status(*, state: str, merged: bool, draft: bool = False) -> str:
    if merged:
        return "merged"
    st = (state or "").lower()
    if draft or st == "draft":
        return "draft"
    if st == "closed":
        return "closed"
    if st == "open":
        return "open"
    return "unknown"


def verify_github_signature(body: bytes, signature_header: str | None, secret: str) -> bool:
    """If secret is empty, skip verification (local/dev only)."""
    if not secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    got = signature_header.split("=", 1)[1].strip()
    return hmac.compare_digest(expected, got)


def extract_pr_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize GitHub pull_request event (or flat fixture) into fields."""
    pr = payload.get("pull_request") or {}
    if not pr and payload.get("html_url"):
        # flat fixture
        pr = payload
    head = pr.get("head") or {}
    repo = payload.get("repository") or {}
    return {
        "action": payload.get("action"),
        "pr_url": pr.get("html_url") or payload.get("pr_url"),
        "number": pr.get("number") if pr.get("number") is not None else payload.get("number"),
        "state": pr.get("state") or payload.get("state") or "open",
        "merged": bool(pr.get("merged") if "merged" in pr else payload.get("merged", False)),
        "draft": bool(pr.get("draft") if "draft" in pr else payload.get("draft", False)),
        "head_ref": head.get("ref") or payload.get("head_ref") or payload.get("branch"),
        "title": pr.get("title") or payload.get("title"),
        "repo_url": repo.get("html_url") or payload.get("repository_html_url"),
    }
