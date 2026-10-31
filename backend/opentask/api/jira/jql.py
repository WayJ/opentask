"""JQL 子集解析器：Orca 自产 JQL → 契约过滤条件

探测报告 §4：Orca 的 ``jira list --filter`` 与 ``jira search`` 是 JQL 的两个
生产方。``list`` 固定生成::

    [assignee = currentUser() AND] [reporter = currentUser() AND]
    statusCategory = Done | statusCategory != Done
    [AND status in ("A", "B")] [AND sprint in openSprints()]
    ORDER BY updated DESC

``search`` 透传任意 JQL。本解析器支持上述全部形态 + 常用手写子集::

    field := assignee | reporter | status | statusCategory | key | issueKey
             | project | summary | text | description | sprint（恒空集）
    op    := = | != | ~ | in
    值    := "引号串"（支持 \\ 与 \" 转义，与 Orca hVt 的转义对齐）
             | currentUser() | 裸词
    排序  := ORDER BY updated [ASC|DESC]（缺省 DESC，Jira 列表语义）

子句间 AND；同一 ``in (...)`` 内是 OR（JQL 语义）——status/key 的
in 列表在子句内取并集，再与其它子句相交。
子集外语法（OR / was / 日期比较 / NOT 等）显式 400（Jira 形状错误体由
调用方包装），不静默吞掉——静默丢子句会让"没搜到"与"不支持"不可区分。

输出 ``JqlFilter``：字段全部 Optional，None = 不过滤；``forced_empty``
表示语义合法但必然空集（如 project = 别的项目、sprint 筛选、矛盾条件），
调用方直接返回空页、不查库。assignee/reporter 的 currentUser() 由调用方
注入当前用户 ID（解析器无请求上下文）。
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set

from opentask.api.tasks.mapping import (
    generic_status_to_issue_set,
    get_contract_mapping,
)

from .errors import jira_bad_request, jira_status_unknown
from .keys import key_to_issue_code

_ORDER_BY_RE = re.compile(
    r"(?:^|\s)order\s+by\s+([A-Za-z_.]+)(?:\s+(asc|desc))?\s*$",
    re.IGNORECASE,
)
_CLAUSE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_.]*)\s*(!=|=|~)\s*(.+)$", re.DOTALL)
_IN_RE = re.compile(
    r"^([A-Za-z][A-Za-z0-9_.]*)\s+in\s*\((.*)\)$", re.IGNORECASE | re.DOTALL
)

# 支持的字段名（小写归一后匹配）
_KNOWN_FIELDS = {
    "assignee", "reporter", "status", "statuscategory", "key", "issuekey",
    "project", "summary", "text", "description",
}


class JqlSyntaxError(Exception):
    """JQL 不在支持子集内（调用方转 400）"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class JqlFilter:
    """JQL 解析结果（调用方据此驱动 list_issues_for_contract）"""

    statuses: Optional[Set[str]] = None  # IssueStatus 集合
    assignee_ref: Optional[str] = None  # 原值（用户 ID/用户名），由路由解析
    assignee_is_current: bool = False
    reporter_ref: Optional[str] = None
    reporter_is_current: bool = False
    issue_codes: Optional[List[str]] = None
    title_kw: Optional[str] = None
    desc_kw: Optional[str] = None
    any_kws: List[str] = field(default_factory=list)
    order: str = "desc"  # Jira 列表缺省最近优先
    forced_empty: bool = False
    # JQL 里的 project 值集合（路由判断：无一为 OPENTASK → 空集）
    project_values: List[str] = field(default_factory=list)

    def constrain_assignee(self, ref: Optional[str], is_current: bool) -> None:
        """第二个 assignee 子句与第一个不一致 → 必然空集（AND 语义）"""
        if self.assignee_ref is not None or self.assignee_is_current:
            if (self.assignee_ref, self.assignee_is_current) != (ref, is_current):
                self.forced_empty = True
        else:
            self.assignee_ref, self.assignee_is_current = ref, is_current

    def constrain_reporter(self, ref: Optional[str], is_current: bool) -> None:
        if self.reporter_ref is not None or self.reporter_is_current:
            if (self.reporter_ref, self.reporter_is_current) != (ref, is_current):
                self.forced_empty = True
        else:
            self.reporter_ref, self.reporter_is_current = ref, is_current

    def intersect_statuses(self, statuses: Set[str]) -> None:
        if self.statuses is None:
            self.statuses = set(statuses)
        else:
            self.statuses &= statuses
        if not self.statuses:
            self.forced_empty = True

    def union_issue_codes(self, codes: List[str]) -> None:
        """key 子句：多个 key = / in 并集后与既有集合求交（AND 语义）"""
        if self.issue_codes is None:
            self.issue_codes = list(codes)
        else:
            kept = [c for c in self.issue_codes if c in codes]
            self.issue_codes = kept
            if not kept:
                self.forced_empty = True


# ============================================================================
# 词法：顶层（引号外）切分
# ============================================================================


def _split_top_level(text: str, separator: str) -> List[str]:
    """按分隔串切分，忽略引号内出现（双/单引号，反斜杠转义）"""
    parts: List[str] = []
    buf: List[str] = []
    i, n, quote = 0, len(text), ""
    lowered = text.lower()
    sep_lower = separator.lower()
    while i < n:
        ch = text[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if (
            lowered.startswith(sep_lower, i)
            and (i == 0 or text[i - 1].isspace())
            and (i + len(separator) >= n or text[i + len(separator)].isspace())
        ):
            parts.append("".join(buf))
            buf = []
            i += len(separator)
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def _unquote(value: str) -> Optional[str]:
    """剥引号 + 反转义（\\\\ → \\，\\" → "）；裸词原样返回；空串 → None"""
    value = value.strip()
    if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
        body = value[1:-1]
        return (
            body.replace("\\\\", "\x00")
            .replace('\\"', '"')
            .replace("\\'", "'")
            .replace("\x00", "\\")
        )
    return value or None


def _split_in_list(raw: str) -> List[str]:
    """in (...) 内部按逗号切分（引号外），元素保留原文（含引号，后统一 _unquote）"""
    items: List[str] = []
    buf: List[str] = []
    quote = ""
    i = 0
    while i < len(raw):
        ch = raw[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < len(raw):
                buf.append(raw[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
        elif ch == ",":
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    items.append("".join(buf))
    return [item for item in items if item.strip()]


# ============================================================================
# 字段语义
# ============================================================================


def _all_issue_statuses() -> Set[str]:
    return set(get_contract_mapping().issue_to_generic)


def _generic_by_display_or_token(value: str) -> str:
    """通用状态 token（ci）或展示名（ci）→ token；未命中抛状态错误"""
    lowered = value.strip().lower()
    for token in get_contract_mapping().generic_to_issue:
        if lowered == token.lower() or lowered == token.replace("_", " "):
            return token
    raise jira_status_unknown(
        f"status 值 {value!r} 不在生效状态词表内", field="jql"
    )


def _category_by_value(value: str) -> str:
    """statusCategory 值（key 或展示名，ci）→ category key"""
    lowered = value.strip().lower()
    mapping = {
        "new": "new", "to do": "new",
        "indeterminate": "indeterminate", "in progress": "indeterminate",
        "done": "done",
    }
    if lowered in mapping:
        return mapping[lowered]
    raise JqlSyntaxError(
        f"statusCategory 值 {value!r} 非法（支持 new/indeterminate/done）"
    )


def _statuses_in_category(category: str) -> Set[str]:
    """类目 → IssueStatus 集合（经通用状态正映射展开，与词表配置联动）"""
    from .converters import generic_to_category

    result: Set[str] = set()
    for token in get_contract_mapping().generic_to_issue:
        if generic_to_category(token) == category:
            result |= generic_status_to_issue_set(token)
    return result


def _is_current_user(value: Optional[str]) -> bool:
    return (value or "").replace(" ", "").lower() == "currentuser()"


def _apply_eq_clause(out: JqlFilter, name: str, op: str, raw_value: str) -> None:
    value = _unquote(raw_value)

    if name in ("assignee", "reporter"):
        if op != "=":
            raise JqlSyntaxError(f"{name} 仅支持 = 比较")
        if _is_current_user(value):
            ref, current = None, True
        elif value is None:
            raise JqlSyntaxError(f"{name} 值为空")
        else:
            ref, current = value, False
        if name == "assignee":
            out.constrain_assignee(ref, current)
        else:
            out.constrain_reporter(ref, current)

    elif name == "status":
        target = _generic_by_display_or_token(value or "")
        statuses = generic_status_to_issue_set(target)
        if op == "=":
            out.intersect_statuses(statuses)
        elif op == "!=":
            out.intersect_statuses(_all_issue_statuses() - statuses)
        else:
            raise JqlSyntaxError("status 仅支持 = / != 比较")

    elif name == "statuscategory":
        category = _category_by_value(value or "")
        statuses = _statuses_in_category(category)
        if op == "=":
            out.intersect_statuses(statuses)
        elif op == "!=":
            out.intersect_statuses(_all_issue_statuses() - statuses)
        else:
            raise JqlSyntaxError("statusCategory 仅支持 = / != 比较")

    elif name in ("key", "issuekey"):
        if op != "=":
            raise JqlSyntaxError("key 仅支持 = 比较（多个请用 key in (...)）")
        try:
            code = key_to_issue_code(value or "")
        except ValueError as e:
            raise JqlSyntaxError(str(e)) from e
        out.union_issue_codes([code])

    elif name == "project":
        if op != "=":
            raise JqlSyntaxError("project 仅支持 = 比较")
        out.project_values.append(value or "")

    elif name in ("summary", "text", "description"):
        if op != "~":
            raise JqlSyntaxError(f"{name} 仅支持 ~ 包含匹配")
        if value is None:
            raise JqlSyntaxError(f"{name} 关键字为空")
        if name == "summary":
            out.title_kw = value
        elif name == "description":
            out.desc_kw = value
        else:
            out.any_kws.append(value)

    else:  # pragma: no cover — _KNOWN_FIELDS 已过滤
        raise JqlSyntaxError(f"不支持的字段: {name}")


def _apply_in_clause(out: JqlFilter, name: str, raw_list: str) -> None:
    values = [v for v in (_unquote(item) for item in _split_in_list(raw_list)) if v]
    if not values:
        raise JqlSyntaxError(f"{name} in (...) 列表为空")

    if name in ("status", "statuscategory"):
        union: Set[str] = set()
        if name == "status":
            for v in values:
                union |= generic_status_to_issue_set(_generic_by_display_or_token(v))
        else:
            for v in values:
                union |= _statuses_in_category(_category_by_value(v))
        out.intersect_statuses(union)

    elif name in ("key", "issuekey"):
        codes: List[str] = []
        for v in values:
            try:
                codes.append(key_to_issue_code(v or ""))
            except ValueError as e:
                raise JqlSyntaxError(str(e)) from e
        out.union_issue_codes(codes)

    elif name == "project":
        out.project_values.extend(values)

    else:
        raise JqlSyntaxError(f"{name} 不支持 in (...) 比较")


def parse_jql(jql: str) -> JqlFilter:
    """解析 JQL 子集；语法外抛 JqlSyntaxError / jira_status_unknown（均 400）"""
    text = (jql or "").strip()
    out = JqlFilter()

    if not text:
        return out

    # ORDER BY 尾部提取（仅支持 updated）
    m = _ORDER_BY_RE.search(text)
    if m:
        order_field = m.group(1).lower()
        if order_field not in ("updated", "updateddate"):
            raise JqlSyntaxError(
                f"ORDER BY 仅支持 updated（当前: {m.group(1)!r}）"
            )
        out.order = (m.group(2) or "desc").lower()
        text = text[: m.start()].strip()

    if not text:
        return out

    for raw_clause in _split_top_level(text, "and"):
        clause = raw_clause.strip()
        if not clause:
            raise JqlSyntaxError("空的条件子句")

        # sprint 系子句（in openSprints() / = N / not in ...）：无 sprint 数据，
        # 任何形式恒为空集——在正则匹配前短路（openSprints() 带参形态
        # 不满足 in (...) 的文法）
        if clause.lower().startswith("sprint"):
            out.forced_empty = True
            continue

        in_match = _IN_RE.match(clause)
        if in_match:
            name = in_match.group(1).lower()
            if name not in _KNOWN_FIELDS:
                raise JqlSyntaxError(f"不支持的字段: {in_match.group(1)!r}")
            _apply_in_clause(out, name, in_match.group(2))
            continue

        op_match = _CLAUSE_RE.match(clause)
        if not op_match:
            raise JqlSyntaxError(f"无法解析的 JQL 子句: {clause!r}")
        name = op_match.group(1).lower()
        if name not in _KNOWN_FIELDS:
            raise JqlSyntaxError(f"不支持的字段: {op_match.group(1)!r}")
        _apply_eq_clause(out, name, op_match.group(2), op_match.group(3))

    return out


def translate_jql(jql: str) -> JqlFilter:
    """parse_jql 的对外入口：语法错误统一转 JiraWireError(400)"""
    try:
        return parse_jql(jql)
    except JqlSyntaxError as e:
        raise jira_bad_request(
            f"JQL 不在支持子集内: {e.message}", field="jql"
        ) from e
