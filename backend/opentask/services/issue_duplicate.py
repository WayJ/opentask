"""E75: Issue duplicate helpers (title suffix; no DB)."""
from __future__ import annotations

COPY_TITLE_SUFFIX = " (copy)"


def build_duplicate_title(title: str, override: str | None = None) -> str:
    """Q3a: ASCII suffix ' (copy)' unless a non-empty override is provided."""
    if override is not None and override.strip():
        return override.strip()
    return f"{title}{COPY_TITLE_SUFFIX}"
