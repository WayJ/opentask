"""Linear-like branch naming: {issue_code}-{slug}."""
from __future__ import annotations

import re
import unicodedata

# KEY-N only (E99): 2–6 alphanumeric prefix
_KEY_N = re.compile(r"\b([A-Za-z][A-Za-z0-9]{1,5}-\d+)\b")
_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify_title(title: str | None, *, max_len: int = 40) -> str:
    if not title:
        return ""
    text = unicodedata.normalize("NFKC", title).lower()
    text = _NON_SLUG.sub("-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if max_len > 0 and len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text


def suggest_branch_name(issue_code: str, title: str | None) -> str:
    code = (issue_code or "").strip()
    if not code:
        raise ValueError("issue_code required")
    slug = slugify_title(title)
    return f"{code}-{slug}" if slug else code


def parse_issue_code_from_branch(branch: str) -> str | None:
    """Extract KEY-N from a branch name. Year legacy ISSUE{year}-N is ignored."""
    if not branch:
        return None
    for m in _KEY_N.finditer(branch):
        code = m.group(1)
        # Prefix longer than 6 (e.g. ISSUE2026) cannot be KEY-N; _KEY_N already caps at 6
        prefix, num = code.rsplit("-", 1)
        return f"{prefix.upper()}-{num}"
    return None
