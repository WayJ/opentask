"""E76: issue link URL validation (Q4a)."""
from __future__ import annotations

import pytest

from opentask.services.issue_link.service import validate_http_url


def test_https_ok():
    assert validate_http_url("https://figma.com/file/x") == "https://figma.com/file/x"


def test_http_ok_strips():
    assert validate_http_url("  http://example.com/a  ") == "http://example.com/a"


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "javascript:alert(1)",
        "/relative",
        "ftp://x.com",
        "notaurl",
        "https://",
        "http://",
        "file:///etc/passwd",
    ],
)
def test_rejects_bad(bad):
    with pytest.raises(ValueError):
        validate_http_url(bad)


def test_rejects_too_long():
    with pytest.raises(ValueError):
        validate_http_url("https://example.com/" + ("a" * 2100))
