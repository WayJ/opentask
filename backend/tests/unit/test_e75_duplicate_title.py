"""E75: duplicate title suffix (Q3a)."""
from __future__ import annotations

from opentask.services.issue_duplicate import COPY_TITLE_SUFFIX, build_duplicate_title


def test_suffix_appended():
    assert build_duplicate_title("Login bug") == "Login bug (copy)"
    assert COPY_TITLE_SUFFIX == " (copy)"


def test_override_wins():
    assert build_duplicate_title("Login bug", override="Custom title") == "Custom title"


def test_empty_override_falls_back():
    assert build_duplicate_title("X", override="") == "X (copy)"
    assert build_duplicate_title("X", override="   ") == "X (copy)"
