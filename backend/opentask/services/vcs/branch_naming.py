"""Linear-like branch naming: {issue_code}-{slug}."""
from __future__ import annotations

import re
import unicodedata

_LEGACY_CODE = re.compile(r"(ISSUE\d{4}-\d+)", re.IGNORECASE)
# KEY-N: 2–6 alphanumeric prefix; exclude strings that are legacy ISSUE{year}
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
    if not branch:
        return None
    legacy = _LEGACY_CODE.search(branch)
    if legacy:
        raw = legacy.group(1)
        # Canonical ISSUE{year}-{n}
        m = re.match(r"issue(\d{4})-(\d+)$", raw, re.IGNORECASE)
        if m:
            return f"ISSUE{m.group(1)}-{m.group(2)}"
        return raw

    for m in _KEY_N.finditer(branch):
        code = m.group(1)
        if re.match(r"ISSUE\d{4}-\d+$", code, re.IGNORECASE):
            continue
        prefix, num = code.rsplit("-", 1)
        return f"{prefix.upper()}-{num}"
    return None
