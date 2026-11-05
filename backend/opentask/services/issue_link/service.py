"""E76: Issue external links service — http(s) bookmarks on Issue."""
from __future__ import annotations

from urllib.parse import urlparse

MAX_LINKS_PER_ISSUE = 50
MAX_URL_LEN = 2048
MAX_TITLE_LEN = 255


def validate_http_url(url: str) -> str:
    """Q4a: only http/https with a non-empty host; reject javascript:/relative/empty."""
    if url is None:
        raise ValueError("url 不能为空")
    normalized = url.strip()
    if not normalized:
        raise ValueError("url 不能为空")
    if len(normalized) > MAX_URL_LEN:
        raise ValueError(f"url 最长 {MAX_URL_LEN} 字符")
    parsed = urlparse(normalized)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("url 仅允许 http:// 或 https://")
    if not parsed.netloc:
        raise ValueError("url 缺少主机名")
    return normalized
