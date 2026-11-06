"""Jira issue key 编解码（OPENTASK-{数字} ↔ KEY-N issue_code）

Orca 侧 key 是不可解析的 opaque 字符串（仅要求 [前缀]-[数字] 形状、稳定、
可回查），见 docs/superpowers/sprints/2026-11-01-S7-orca-jira-probe.md §5。

编码方案（E99）：仅 **KEY-N** ``{KEY}-{N}``（KEY 为 2–6 位 [A-Z0-9]）：
落在 ``KEY_N_BASE`` 以上的独立号段，前缀用 radix-37（含 pad）打包，
序号容量 ``KEY_N_SEQ_CAP``。

年号 legacy ``ISSUE{year}-N`` 与 ``number < KEY_N_BASE`` 的解码路径已删除；
此类输入一律 ``ValueError``。

序号越界 / 无法识别形状 → ValueError。key 前缀大小写不敏感；编码恒为大写。
"""

from __future__ import annotations

import re
from typing import Final

KEY_PREFIX: Final = "OPENTASK"
# KEY-N（E12/E99）：OT-1 / WAY-42
_KEY_N_RE = re.compile(r"^([A-Z][A-Z0-9]{1,5})-(\d+)$", re.IGNORECASE)
# Jira key 形状（前缀大小写不敏感）
_KEY_RE = re.compile(rf"^{KEY_PREFIX}-(\d+)$", re.IGNORECASE)

# 历史 year 公式容量常数：仅用于 KEY_N_BASE 定位（高于任何旧 year*1e9）
_SEQ_CAPACITY_LEGACY_FLOOR: Final = 1_000_000_000

# KEY-N 号段：高于任何旧 year*SEQ 编码，且整体 < JS Number.MAX_SAFE_INTEGER
KEY_N_BASE: Final = 10_000 * _SEQ_CAPACITY_LEGACY_FLOOR  # 1e13
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
    """KEY-N issue_code → Jira key ``OPENTASK-{n}``.

    Raises:
        ValueError: 非 KEY-N、年号 legacy、或序号超出投影容量。
    """
    code = issue_code or ""
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
    """Jira key → KEY-N issue_code（失败抛 ValueError，调用方转 400/404）。

    ``number < KEY_N_BASE``（旧年号投影）一律拒绝。
    """
    m = _KEY_RE.match((key or "").strip())
    if not m:
        raise ValueError(f"无法识别的 Jira key: {key!r}")
    number = int(m.group(1))
    if number < KEY_N_BASE:
        raise ValueError(
            f"Jira key {key!r} 低于 KEY-N 号段（年号 legacy 投影已移除）"
        )
    rem = number - KEY_N_BASE
    packed, seq = divmod(rem, KEY_N_SEQ_CAP)
    prefix = _int_to_prefix(packed)
    return f"{prefix}-{seq}"
