"""E11-S1: Linear-like branch naming helpers."""
from __future__ import annotations

from opentask.services.vcs.branch_naming import (
    parse_issue_code_from_branch,
    slugify_title,
    suggest_branch_name,
)


def test_slugify_basic():
    assert slugify_title("Fix Login Redirect!") == "fix-login-redirect"


def test_slugify_unicode_and_collapse():
    assert slugify_title("  Hello---World  ") == "hello-world"
    assert slugify_title("登录修复 ABC") == "abc"


def test_slugify_empty():
    assert slugify_title("") == ""
    assert slugify_title(None) == ""


def test_slugify_max_len():
    long = "a" * 100
    assert len(slugify_title(long, max_len=40)) <= 40


def test_suggest_with_title():
    assert suggest_branch_name("WAY-42", "Fix Login Redirect") == "WAY-42-fix-login-redirect"


def test_suggest_empty_title():
    assert suggest_branch_name("WAY-42", "") == "WAY-42"
    assert suggest_branch_name("WAY-42", None) == "WAY-42"


def test_parse_key_n():
    assert parse_issue_code_from_branch("feature/WAY-42-fix-login") == "WAY-42"
    assert parse_issue_code_from_branch("WAY-42-fix-login-redirect") == "WAY-42"


def test_parse_year_legacy_ignored():
    # E99: year codes are not product identifiers; prefix ISSUE2026 is >6 chars
    assert parse_issue_code_from_branch("ISSUE2026-3-something") is None


def test_parse_none():
    assert parse_issue_code_from_branch("main") is None
    assert parse_issue_code_from_branch("") is None
