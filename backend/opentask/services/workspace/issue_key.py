"""Workspace issue_key 校验与从 slug 派生（E12-S1）"""
from __future__ import annotations

import re

_KEY_RE = re.compile(r"^[A-Z0-9]{2,6}$")
_SLUG_ALNUM = re.compile(r"[^A-Z0-9]")


def normalize_issue_key(raw: str) -> str:
    key = (raw or "").strip().upper()
    if not _KEY_RE.fullmatch(key):
        raise ValueError("issue_key 须为 2–6 位大写字母或数字")
    return key


def derive_issue_key_from_slug(slug: str) -> str:
    raw = _SLUG_ALNUM.sub("", (slug or "").upper())
    if len(raw) >= 2:
        return raw[:6]
    if len(raw) == 1:
        return (raw + "T")[:2]
    return "OT"
