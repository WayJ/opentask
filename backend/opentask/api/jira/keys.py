"""Jira issue key 编解码（OPENTASK-{数字} ↔ issue_code）

Orca 侧 key 是不可解析的 opaque 字符串（仅要求 [前缀]-[数字] 形状、稳定、
可回查），见 docs/superpowers/sprints/2026-11-01-S7-orca-jira-probe.md §5。

编码方案：数字 = 年份 × 1 000 000 000 + 年内序号（issue_code 为
``ISSUE{年}-{序号}``，序号按年重置；直接用裸序号会在跨年时把两个不同
issue 投影成同一 key，故把年份编进数字保证单射 + 可逆）::

    ISSUE2026-3  →  OPENTASK-202600000003
    OPENTASK-202600000003  →  ISSUE2026-3

序号 ≥ 10^9（单年十亿条以上，含测试种子用的 9 亿段以外更高段）超出
本投影容量：编码方向抛 ValueError（调用方可见，不静默撞号）；解码方向
年份落在 [2000, 9999] 外同样拒绝。key 前缀大小写不敏感（Jira key 惯例），
编码恒为大写。
"""

import re
from typing import Final

KEY_PREFIX: Final = "OPENTASK"
# issue_code 形状：ISSUE2026-3
_ISSUE_CODE_RE = re.compile(r"^ISSUE(\d{4})-(\d+)$")
# Jira key 形状（前缀大小写不敏感）：opentask-202600000003
_KEY_RE = re.compile(rf"^{KEY_PREFIX}-(\d+)$", re.IGNORECASE)

# 单年序号容量（数字编码 = year * SEQ_CAPACITY + seq）
SEQ_CAPACITY: Final = 1_000_000_000
_MIN_YEAR: Final = 2000
_MAX_YEAR: Final = 9999


def issue_code_to_key(issue_code: str) -> str:
    """issue_code → Jira key（OPENTASK-{年*100000+序号}）

    Raises:
        ValueError: issue_code 非法或序号超出投影容量。
    """
    m = _ISSUE_CODE_RE.match(issue_code or "")
    if not m:
        raise ValueError(f"无法识别的 issue_code: {issue_code!r}")
    year, seq = int(m.group(1)), int(m.group(2))
    if seq >= SEQ_CAPACITY:
        raise ValueError(
            f"issue_code {issue_code!r} 序号超出 Jira key 投影容量"
            f"（{SEQ_CAPACITY}）"
        )
    return f"{KEY_PREFIX}-{year * SEQ_CAPACITY + seq}"


def key_to_issue_code(key: str) -> str:
    """Jira key → issue_code（解码失败抛 ValueError，调用方转 400/404）"""
    m = _KEY_RE.match((key or "").strip())
    if not m:
        raise ValueError(f"无法识别的 Jira key: {key!r}")
    year, seq = divmod(int(m.group(1)), SEQ_CAPACITY)
    if not (_MIN_YEAR <= year <= _MAX_YEAR):
        raise ValueError(f"Jira key {key!r} 解出的年份超出范围: {year}")
    return f"ISSUE{year}-{seq}"
