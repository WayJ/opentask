"""Jira issue key 编解码（OPENTASK-{数字} ↔ issue_code）

Orca 侧 key 是不可解析的 opaque 字符串（仅要求 [前缀]-[数字] 形状、稳定、
可回查），见 docs/superpowers/sprints/2026-11-01-S7-orca-jira-probe.md §5。

编码方案：

1. **Legacy** ``ISSUE{年}-{序号}``：数字 = 年份 × 1_000_000_000 + 年内序号::

       ISSUE2026-3  →  OPENTASK-2026000000003
       OPENTASK-2026000000003  →  ISSUE2026-3

2. **E12 KEY-N** ``{KEY}-{N}``（KEY 为 2–6 位 [A-Z0-9]）：落在
   ``KEY_N_BASE`` 以上的独立号段，前缀用 radix-37（含 pad）打包，
   序号容量 ``KEY_N_SEQ_CAP``（不改写 legacy 年号公式）。

序号越界 / 无法识别形状 → ValueError。key 前缀大小写不敏感；编码恒为大写。
"""

from __future__ import annotations

import re
from typing import Final

KEY_PREFIX: Final = "OPENTASK"
# issue_code 形状：ISSUE2026-3
_ISSUE_CODE_RE = re.compile(r"^ISSUE(\d{4})-(\d+)$")
# KEY-N（E12）：OT-1 / WAY-42；排除已被 legacy 吃掉的 ISSUE{year}-N
_KEY_N_RE = re.compile(r"^([A-Z][A-Z0-9]{1,5})-(\d+)$", re.IGNORECASE)
# Jira key 形状（前缀大小写不敏感）：opentask-2026000000003
_KEY_RE = re.compile(rf"^{KEY_PREFIX}-(\d+)$", re.IGNORECASE)

# 单年序号容量（数字编码 = year * SEQ_CAPACITY + seq）
SEQ_CAPACITY: Final = 1_000_000_000
_MIN_YEAR: Final = 2000
_MAX_YEAR: Final = 9999

# KEY-N 号段：高于任何合法 year*SEQ_CAPACITY，且整体 < JS Number.MAX_SAFE_INTEGER
KEY_N_BASE: Final = 10_000 * SEQ_CAPACITY  # 1e13
KEY_N_SEQ_CAP: Final = 1_000_000
_ALPH37: Final = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # 0..35；pad=36


def _prefix_to_int(prefix: str) -> int:
    p = (prefix or "").upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,5}", p):
        raise ValueError(f"非法 issue_key 前缀: {prefix!r}")
    chars = list(p.ljust(6, "\x00"))
    n = 0
    for ch in chars:
        v = 36 if ch == "\x00" else _ALPH37.index(ch)
        n = n * 37 + v
    return n


def _int_to_prefix(n: int) -> str:
    if n < 0:
        raise ValueError("负前缀编码")
    chars: list[str] = []
    for _ in range(6):
        n, rem = divmod(n, 37)
        chars.append("\x00" if rem == 36 else _ALPH37[rem])
    if n != 0:
        raise ValueError("前缀编码溢出")
    chars.reverse()
    raw = "".join(chars).rstrip("\x00")
    if len(raw) < 2:
        raise ValueError("解码前缀过短")
    return raw


def issue_code_to_key(issue_code: str) -> str:
    """issue_code → Jira key（legacy ISSUE{year}-N 或 E12 KEY-N）

    Raises:
        ValueError: issue_code 非法或序号超出投影容量。
    """
    code = issue_code or ""
    m = _ISSUE_CODE_RE.match(code)
    if m:
        year, seq = int(m.group(1)), int(m.group(2))
        if seq >= SEQ_CAPACITY:
            raise ValueError(
                f"issue_code {issue_code!r} 序号超出 Jira key 投影容量"
                f"（{SEQ_CAPACITY}）"
            )
        return f"{KEY_PREFIX}-{year * SEQ_CAPACITY + seq}"

    m2 = _KEY_N_RE.match(code)
    if m2:
        prefix, seq_s = m2.group(1), m2.group(2)
        seq = int(seq_s)
        if seq >= KEY_N_SEQ_CAP:
            raise ValueError(
                f"issue_code {issue_code!r} KEY-N 序号超出 Jira key 投影容量"
                f"（{KEY_N_SEQ_CAP}）"
            )
        packed = _prefix_to_int(prefix)
        number = KEY_N_BASE + packed * KEY_N_SEQ_CAP + seq
        return f"{KEY_PREFIX}-{number}"

    raise ValueError(f"无法识别的 issue_code: {issue_code!r}")


def key_to_issue_code(key: str) -> str:
    """Jira key → issue_code（解码失败抛 ValueError，调用方转 400/404）"""
    m = _KEY_RE.match((key or "").strip())
    if not m:
        raise ValueError(f"无法识别的 Jira key: {key!r}")
    number = int(m.group(1))
    if number >= KEY_N_BASE:
        rem = number - KEY_N_BASE
        packed, seq = divmod(rem, KEY_N_SEQ_CAP)
        prefix = _int_to_prefix(packed)
        return f"{prefix}-{seq}"

    year, seq = divmod(number, SEQ_CAPACITY)
    if not (_MIN_YEAR <= year <= _MAX_YEAR):
        raise ValueError(f"Jira key {key!r} 解出的年份超出范围: {year}")
    return f"ISSUE{year}-{seq}"
