"""E40 Formula expression sandbox — restricted AST interpreter (no eval/exec)."""
from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Optional

MAX_EXPR_LEN = 500
MAX_FN_ARGS = 8
MAX_AST_NODES = 200
MAX_FORMULA_DEPTH = 8

RESULT_TYPES = ("number", "boolean", "text", "date")

_CF_RE = re.compile(r"\bcf\.([a-z][a-z0-9_-]{0,63})\b")
_ISSUE_RE = re.compile(r"\bissue\.(estimate_points|priority|status)\b")
_TRUE_RE = re.compile(r"\btrue\b")
_FALSE_RE = re.compile(r"\bfalse\b")
_NULL_RE = re.compile(r"\bnull\b")

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_ALLOWED_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
}
_ALLOWED_CMP = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}
_FN_NAMES = frozenset(
    {
        "IF",
        "COALESCE",
        "ABS",
        "MIN",
        "MAX",
        "ROUND",
        "LEN",
        "LOWER",
        "UPPER",
        "DATE_DIFF",
        "__cf__",
        "__issue__",
    }
)
_BARE_NAMES = frozenset({"days_until_due"})


class FormulaError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


@dataclass
class ParsedFormula:
    expr: str
    tree: ast.AST
    dependencies: list[str]  # e.g. ["cf.weight"]
    cf_keys: list[str]


def preprocess(expr: str) -> tuple[str, list[str], list[str]]:
    """Rewrite cf.*/issue.* and true/false/null for Python AST parse."""
    deps: list[str] = []
    cf_keys: list[str] = []

    def _cf(m: re.Match) -> str:
        key = m.group(1)
        dep = f"cf.{key}"
        if dep not in deps:
            deps.append(dep)
            cf_keys.append(key)
        return f'__cf__("{key}")'

    def _issue(m: re.Match) -> str:
        field = m.group(1)
        dep = f"issue.{field}"
        if dep not in deps:
            deps.append(dep)
        return f'__issue__("{field}")'

    s = _CF_RE.sub(_cf, expr)
    s = _ISSUE_RE.sub(_issue, s)
    s = _TRUE_RE.sub("True", s)
    s = _FALSE_RE.sub("False", s)
    s = _NULL_RE.sub("None", s)
    return s, deps, cf_keys


def _count_nodes(tree: ast.AST) -> int:
    return sum(1 for _ in ast.walk(tree))


def _assert_whitelist(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.Expression,
                ast.Constant,
                ast.Load,
                ast.And,
                ast.Or,
            ),
        ):
            continue
        if isinstance(node, ast.Name):
            if node.id in ("True", "False", "None"):
                continue
            if node.id in _BARE_NAMES or node.id in _FN_NAMES:
                continue
            raise FormulaError("parse_error", f"非法标识符: {node.id}")
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
            continue
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
            continue
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            continue
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if type(op) not in _ALLOWED_CMP:
                    raise FormulaError("parse_error", "非法比较运算符")
            continue
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _FN_NAMES:
                raise FormulaError("parse_error", "非法函数调用")
            if node.keywords:
                raise FormulaError("parse_error", "不允许关键字参数")
            if len(node.args) > MAX_FN_ARGS:
                raise FormulaError("parse_error", f"函数参数最多 {MAX_FN_ARGS}")
            continue
        if isinstance(
            node,
            (
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.Div,
                ast.UAdd,
                ast.USub,
                ast.Not,
                ast.Eq,
                ast.NotEq,
                ast.Lt,
                ast.LtE,
                ast.Gt,
                ast.GtE,
            ),
        ):
            continue
        # Explicit bans
        if isinstance(
            node,
            (
                ast.Attribute,
                ast.Subscript,
                ast.Lambda,
                ast.ListComp,
                ast.SetComp,
                ast.DictComp,
                ast.GeneratorExp,
                ast.Dict,
                ast.List,
                ast.Tuple,
                ast.Set,
                ast.JoinedStr,
                ast.FormattedValue,
                ast.Await,
                ast.Yield,
                ast.Starred,
                ast.IfExp,
            ),
        ):
            raise FormulaError("parse_error", f"禁止节点: {type(node).__name__}")
        raise FormulaError("parse_error", f"禁止节点: {type(node).__name__}")


def parse_formula(expr: str) -> ParsedFormula:
    if expr is None or not str(expr).strip():
        raise FormulaError("parse_error", "表达式不能为空")
    raw = str(expr)
    if len(raw) > MAX_EXPR_LEN:
        raise FormulaError("parse_error", f"表达式最长 {MAX_EXPR_LEN} 字符")
    rewritten, deps, cf_keys = preprocess(raw)
    try:
        tree = ast.parse(rewritten, mode="eval")
    except SyntaxError as e:
        raise FormulaError("parse_error", f"语法错误: {e.msg}") from e
    if _count_nodes(tree) > MAX_AST_NODES:
        raise FormulaError("parse_error", f"AST 节点数超过 {MAX_AST_NODES}")
    _assert_whitelist(tree)
    return ParsedFormula(expr=raw, tree=tree, dependencies=deps, cf_keys=cf_keys)


def _as_number(v: Any) -> float:
    if isinstance(v, bool) or v is None:
        raise FormulaError("type_error")
    if isinstance(v, (int, float)):
        return float(v)
    raise FormulaError("type_error")


def _as_text(v: Any) -> str:
    if v is None:
        raise FormulaError("type_error")
    if isinstance(v, str):
        return v
    raise FormulaError("type_error")


def _parse_date(v: Any) -> date:
    if v is None:
        raise FormulaError("type_error")
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        return date.fromisoformat(v)
    raise FormulaError("type_error")


def _truthy_bool(v: Any) -> bool:
    if not isinstance(v, bool):
        raise FormulaError("type_error")
    return v


class _Interpreter:
    def __init__(
        self,
        *,
        cf_get: Callable[[str], Any],
        issue_get: Callable[[str], Any],
        days_until_due: Any,
    ):
        self.cf_get = cf_get
        self.issue_get = issue_get
        self.days_until_due = days_until_due

    def eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return self.eval(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id == "days_until_due":
                return self.days_until_due
            if node.id == "True":
                return True
            if node.id == "False":
                return False
            if node.id == "None":
                return None
            raise FormulaError("parse_error", f"非法标识符: {node.id}")
        if isinstance(node, ast.UnaryOp):
            op = _ALLOWED_UNARY[type(node.op)]
            val = self.eval(node.operand)
            if isinstance(node.op, ast.Not):
                return op(_truthy_bool(val))
            return op(_as_number(val))
        if isinstance(node, ast.BinOp):
            left = self.eval(node.left)
            right = self.eval(node.right)
            op_t = type(node.op)
            if op_t is ast.Add and isinstance(left, str) and isinstance(right, str):
                return left + right
            try:
                ln = _as_number(left)
                rn = _as_number(right)
            except FormulaError:
                raise FormulaError("type_error")
            if op_t is ast.Div:
                if rn == 0:
                    raise FormulaError("div_zero")
                return ln / rn
            return _ALLOWED_BINOPS[op_t](ln, rn)
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for v in node.values:
                    cur = self.eval(v)
                    if not _truthy_bool(cur):
                        return False
                return True
            # Or
            for v in node.values:
                cur = self.eval(v)
                if _truthy_bool(cur):
                    return True
            return False
        if isinstance(node, ast.Compare):
            left = self.eval(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self.eval(comparator)
                fn = _ALLOWED_CMP[type(op)]
                # allow null equality
                if type(op) in (ast.Eq, ast.NotEq):
                    ok = fn(left, right)
                else:
                    if left is None or right is None:
                        raise FormulaError("type_error")
                    if isinstance(left, str) and isinstance(right, str):
                        ok = fn(left, right)
                    else:
                        ok = fn(_as_number(left), _as_number(right))
                if not ok:
                    return False
                left = right
            return True
        if isinstance(node, ast.Call):
            assert isinstance(node.func, ast.Name)
            name = node.func.id
            args = [self.eval(a) for a in node.args]
            return self._call(name, args)
        raise FormulaError("parse_error", f"无法求值: {type(node).__name__}")

    def _call(self, name: str, args: list[Any]) -> Any:
        if name == "__cf__":
            if len(args) != 1 or not isinstance(args[0], str):
                raise FormulaError("parse_error")
            try:
                return self.cf_get(args[0])
            except FormulaError:
                raise
            except Exception as e:
                if isinstance(e, FormulaError):
                    raise
                raise FormulaError("dep_error") from e
        if name == "__issue__":
            if len(args) != 1 or not isinstance(args[0], str):
                raise FormulaError("parse_error")
            return self.issue_get(args[0])
        if name == "IF":
            if len(args) != 3:
                raise FormulaError("parse_error", "IF 需要 3 个参数")
            return args[1] if _truthy_bool(args[0]) else args[2]
        if name == "COALESCE":
            if not args:
                raise FormulaError("parse_error", "COALESCE 需要参数")
            for a in args:
                if a is not None:
                    return a
            return None
        if name == "ABS":
            if len(args) != 1:
                raise FormulaError("parse_error")
            return abs(_as_number(args[0]))
        if name == "MIN":
            if len(args) < 1:
                raise FormulaError("parse_error")
            return min(_as_number(a) for a in args)
        if name == "MAX":
            if len(args) < 1:
                raise FormulaError("parse_error")
            return max(_as_number(a) for a in args)
        if name == "ROUND":
            if len(args) not in (1, 2):
                raise FormulaError("parse_error")
            n = 0 if len(args) == 1 else int(_as_number(args[1]))
            return round(_as_number(args[0]), n)
        if name == "LEN":
            if len(args) != 1:
                raise FormulaError("parse_error")
            return len(_as_text(args[0]))
        if name == "LOWER":
            if len(args) != 1:
                raise FormulaError("parse_error")
            return _as_text(args[0]).lower()
        if name == "UPPER":
            if len(args) != 1:
                raise FormulaError("parse_error")
            return _as_text(args[0]).upper()
        if name == "DATE_DIFF":
            if len(args) != 2:
                raise FormulaError("parse_error")
            if args[0] is None or args[1] is None:
                return None
            a = _parse_date(args[0])
            b = _parse_date(args[1])
            return (a - b).days
        raise FormulaError("parse_error", f"未知函数 {name}")


def coerce_result(value: Any, result_type: str) -> Any:
    if value is None:
        return None
    rt = result_type or "number"
    if rt == "number":
        if isinstance(value, bool):
            raise FormulaError("type_error")
        if isinstance(value, (int, float)):
            # prefer int when whole
            if isinstance(value, float) and value.is_integer():
                return int(value)
            return value if isinstance(value, int) else float(value)
        raise FormulaError("type_error")
    if rt == "boolean":
        if isinstance(value, bool):
            return value
        raise FormulaError("type_error")
    if rt == "text":
        if isinstance(value, str):
            return value
        # allow coerce numbers to text? design says type_error on mismatch — strict
        raise FormulaError("type_error")
    if rt == "date":
        if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return value
        if isinstance(value, date) and not isinstance(value, datetime):
            return value.isoformat()
        raise FormulaError("type_error")
    raise FormulaError("type_error")


def eval_parsed(
    parsed: ParsedFormula,
    *,
    cf_get: Callable[[str], Any],
    issue_get: Callable[[str], Any],
    days_until_due: Any,
    result_type: str = "number",
) -> tuple[Any, Optional[str]]:
    """Return (value, error_code). Never raises to caller for FormulaError."""
    try:
        interp = _Interpreter(
            cf_get=cf_get, issue_get=issue_get, days_until_due=days_until_due
        )
        raw = interp.eval(parsed.tree)
        return coerce_result(raw, result_type), None
    except FormulaError as e:
        return None, e.code


def days_until_due_value(issue: Any, today: Optional[date] = None) -> Optional[int]:
    today = today or datetime.utcnow().date()
    due = getattr(issue, "due_date", None)
    if due is None:
        return None
    if isinstance(due, datetime):
        d = due.date()
    elif isinstance(due, date):
        d = due
    elif isinstance(due, str) and re.match(r"^\d{4}-\d{2}-\d{2}", due):
        d = date.fromisoformat(due[:10])
    else:
        return None
    return (d - today).days


def issue_field_value(issue: Any, name: str) -> Any:
    if name == "estimate_points":
        return getattr(issue, "estimate_points", None)
    if name == "priority":
        return getattr(issue, "priority", None)
    if name == "status":
        return getattr(issue, "status", None)
    raise FormulaError("parse_error", f"未知 issue 字段: {name}")
