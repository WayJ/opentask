"""字段映射与契约配置层：通用任务模型 ↔ OpenTask Issue 转换 + 契约段配置

职责（epic ADR D7/D12 + sprint S4 D1/D2/D3 + S5 映射配置化 + S6 禁操作配置）：
- 状态映射表：IssueStatus（open/in_progress/feedback/resolved/closed/rejected）
  ↔ 通用状态（默认 todo/in_progress/in_review/done/cancelled，可经
  config/*.yaml 的 contract.status_mapping 段整体替换）
- 禁操作表：contract.forbidden_operations 可禁用部分契约操作
  （默认空 = 全放行；被禁操作请求 → 403 CONTRACT_FORBIDDEN，见 errors.py）
- 配置优先、代码默认表兜底（未配置段时）；配置存在但非法时快速失败
  （拒绝静默降级——操作者以为生效的映射与实际不符比报错更危险）
- issue→generic 为全函数（6 → 5，resolved 与 closed 均归 done）；
  generic→issue 取规范逆（枚举声明序在前者优先，默认表 done→resolved），
  因此 generic→issue→generic 对全部通用状态保持恒等（往返无损）。
- 映射结果进程内缓存；改配置需重启进程（与 yaml 其余配置一致），
  测试经 reset_contract_mapping_cache() 显式失效。

POST 落库经 IssueService（业务逻辑与 UI 侧一致），本模块只做形状转换。
模型对象 → 契约 Schema 的组装函数在 converters.py（避免 schemas 循环导入）。
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

from opentask.config import load_config_file
from opentask.models.issue.enums import IssueStatus, IssueType

logger = logging.getLogger(__name__)

# ============================================================================
# 状态映射默认表（未配置 contract.status_mapping 时的代码兜底）
# ============================================================================

DEFAULT_ISSUE_STATUS_TO_GENERIC: Dict[str, str] = {
    IssueStatus.OPEN.value: "todo",
    IssueStatus.IN_PROGRESS.value: "in_progress",
    IssueStatus.FEEDBACK.value: "in_review",
    IssueStatus.RESOLVED.value: "done",
    IssueStatus.CLOSED.value: "done",
    IssueStatus.REJECTED.value: "cancelled",
}

DEFAULT_GENERIC_STATUS_TO_ISSUE: Dict[str, str] = {
    "todo": IssueStatus.OPEN.value,
    "in_progress": IssueStatus.IN_PROGRESS.value,
    "in_review": IssueStatus.FEEDBACK.value,
    "done": IssueStatus.RESOLVED.value,
    "cancelled": IssueStatus.REJECTED.value,
}

DEFAULT_ISSUE_TYPE = "feature"

# 全部合法 IssueStatus（配置表必须逐一覆盖）
_ALL_ISSUE_STATUSES = frozenset(s.value for s in IssueStatus)

# 全部合法 IssueType（contract.default_issue_type 必须在词表内）
_ALL_ISSUE_TYPES = frozenset(s.value for s in IssueType)

# 前端 issue 详情页路由（frontend/src/router/routes/index.ts: issue_detail）
ISSUE_DETAIL_PATH = "/issue/detail"

# 可禁用的契约操作名（与 GET /capabilities.endpoints 的能力键一致；
# token/capabilities 为协商与换 token 所需，不参与禁用）
CONTRACT_OPERATIONS = frozenset(
    {"list_tasks", "create_task", "get_task", "update_task", "delete_task"}
)


class ContractConfigError(RuntimeError):
    """contract 配置段非法（映射缺状态/未知状态/未知操作名/值类型错误等）"""


# 兼容别名（S5 命名；S6 泛化为整段配置校验后保留旧名）
StatusMappingConfigError = ContractConfigError


@dataclass(frozen=True)
class ContractMapping:
    """生效中的契约配置（状态映射 + 禁操作表；配置来源或代码默认）"""

    issue_to_generic: Dict[str, str]
    generic_to_issue: Dict[str, str]
    default_issue_type: str
    # "config"：读自 yaml contract 段；"default"：未配置，代码默认表
    source: str
    # 被禁用的契约操作名集合（contract.forbidden_operations，默认空 = 全放行）
    forbidden_operations: frozenset = frozenset()


def _load_contract_config() -> Dict:
    """读 yaml 的 contract 段（default → 环境配置 → local 深合并）；无则空 dict"""
    environment = os.getenv("APP_ENV", "development")
    try:
        cfg = load_config_file(environment)
    except Exception as e:  # yaml 解析失败等：按「读不到配置」处理并留痕
        logger.warning("读取契约配置失败（%s），回退代码默认表: %s", environment, e)
        return {}
    section = cfg.get("contract")
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ContractConfigError(
            "contract 配置段必须是映射（当前类型: %s）" % type(section).__name__
        )
    return section


def _validate_status_mapping(configured: Dict) -> Dict[str, str]:
    """校验配置的状态映射表并归一为 {issue_status: generic}

    要求：key 恰好覆盖全部 6 种 IssueStatus；value 为非空字符串。
    """
    if not isinstance(configured, dict):
        raise ContractConfigError(
            "contract.status_mapping 必须是映射表（IssueStatus → 通用状态）"
        )

    unknown = sorted(set(configured) - _ALL_ISSUE_STATUSES)
    if unknown:
        raise ContractConfigError(
            f"contract.status_mapping 含未知 IssueStatus: {unknown}，"
            f"合法值: {sorted(_ALL_ISSUE_STATUSES)}"
        )
    missing = sorted(_ALL_ISSUE_STATUSES - set(configured))
    if missing:
        raise ContractConfigError(
            f"contract.status_mapping 缺少 IssueStatus: {missing}（必须全覆盖，"
            "否则该方向映射非全函数）"
        )

    forward: Dict[str, str] = {}
    for key, value in configured.items():
        if not isinstance(value, str) or not value.strip():
            raise ContractConfigError(
                f"contract.status_mapping[{key!r}] 的值必须是非空字符串（当前: {value!r}）"
            )
        forward[key] = value.strip()
    return forward


def _canonical_reverse(forward: Dict[str, str]) -> Dict[str, str]:
    """由正向表推导规范逆 {generic: issue_status}

    同一通用状态对应多个 IssueStatus 时取枚举声明序在前者
    （默认表 done ← resolved/closed → resolved），与文档顺序无关，往返确定。
    """
    reverse: Dict[str, str] = {}
    for status in IssueStatus:  # 枚举声明序
        generic = forward[status.value]
        reverse.setdefault(generic, status.value)
    return reverse


def _validate_forbidden_operations(configured) -> frozenset:
    """校验 contract.forbidden_operations 并归一为冻结集合

    要求：列表、元素为非空字符串、且都在 CONTRACT_OPERATIONS 词表内；
    非法值快速失败（与 status_mapping 同一"拒绝静默降级"原则）。
    """
    if configured is None:
        return frozenset()
    if not isinstance(configured, (list, tuple)):
        raise ContractConfigError(
            "contract.forbidden_operations 必须是操作名列表（当前类型: "
            f"{type(configured).__name__}）"
        )
    names: list = []
    for item in configured:
        if not isinstance(item, str) or not item.strip():
            raise ContractConfigError(
                f"contract.forbidden_operations 元素必须是非空字符串（当前: {item!r}）"
            )
        name = item.strip()
        if name not in CONTRACT_OPERATIONS:
            raise ContractConfigError(
                f"contract.forbidden_operations 含未知操作名: {name!r}，"
                f"合法值: {sorted(CONTRACT_OPERATIONS)}"
            )
        names.append(name)
    return frozenset(names)


def _build_contract_mapping() -> ContractMapping:
    """组装生效配置：配置优先，未配置（或段缺失）回退代码默认表"""
    try:
        section = _load_contract_config()
    except ContractConfigError:
        raise  # 段存在但结构非法 → 快速失败，不静默降级

    status_cfg = section.get("status_mapping")
    if status_cfg is None:
        forward = dict(DEFAULT_ISSUE_STATUS_TO_GENERIC)
        reverse = dict(DEFAULT_GENERIC_STATUS_TO_ISSUE)
        source = "default"
    else:
        forward = _validate_status_mapping(status_cfg)
        reverse = _canonical_reverse(forward)
        source = "config"

    default_issue_type = section.get("default_issue_type", DEFAULT_ISSUE_TYPE)
    if not isinstance(default_issue_type, str) or not default_issue_type.strip():
        raise ContractConfigError(
            f"contract.default_issue_type 必须是非空字符串（当前: {default_issue_type!r}）"
        )
    default_issue_type = default_issue_type.strip()
    if default_issue_type not in _ALL_ISSUE_TYPES:
        # 与 status_mapping 同一"非法配置快速失败"原则：落库 type 词表外的值
        # 会把脏数据写进 issues.type，且契约层无从转换
        raise ContractConfigError(
            f"contract.default_issue_type 含未知 IssueType: {default_issue_type!r}，"
            f"合法值: {sorted(_ALL_ISSUE_TYPES)}"
        )

    forbidden = _validate_forbidden_operations(
        section.get("forbidden_operations")
    )

    return ContractMapping(
        issue_to_generic=forward,
        generic_to_issue=reverse,
        default_issue_type=default_issue_type.strip(),
        source=source,
        forbidden_operations=forbidden,
    )


# ============================================================================
# 生效映射缓存（进程内；改配置需重启，测试用 reset 显式失效）
# ============================================================================

_mapping_cache: Optional[ContractMapping] = None


def reset_contract_mapping_cache() -> None:
    """失效映射缓存（测试钩子；生产改 yaml 后重启进程生效）"""
    global _mapping_cache
    _mapping_cache = None


def get_contract_mapping() -> ContractMapping:
    """取生效映射表（首次访问时从配置加载并缓存）"""
    global _mapping_cache
    if _mapping_cache is None:
        _mapping_cache = _build_contract_mapping()
    return _mapping_cache


def get_generic_statuses() -> frozenset:
    """生效的通用状态词表（即逆向表的 key 集，随配置可变）"""
    return frozenset(get_contract_mapping().generic_to_issue)


def get_default_issue_type() -> str:
    """契约层落库的默认 issue 类型（contract.default_issue_type，兜底 feature）"""
    return get_contract_mapping().default_issue_type


def get_default_generic_status() -> str:
    """POST /tasks 未携带 status 时的默认通用状态（自生效配置推导，不硬编码）

    词表含 todo 时取 todo（与默认表语义一致）；配置词表合法地省略 todo 时
    取规范序（IssueStatus 声明序推导的 generic_to_issue 迭代序）首个，
    保证默认值永远在生效词表内（硬编码 "todo" 在该场景会 500）。
    """
    reverse = get_contract_mapping().generic_to_issue
    if "todo" in reverse:
        return "todo"
    return next(iter(reverse))


def get_forbidden_operations() -> frozenset:
    """生效的禁操作表（contract.forbidden_operations，默认空 = 全放行）

    被禁操作的路由在鉴权通过后、业务逻辑前校验并返回
    403 CONTRACT_FORBIDDEN（顺序保证 401 优先于 403）。
    """
    return get_contract_mapping().forbidden_operations


# ============================================================================
# 转换函数（S5 配置化后签名不变；表来自 get_contract_mapping）
# ============================================================================


def issue_status_to_generic(status: str) -> str:
    """IssueStatus → 通用状态（全函数：全部 6 种 IssueStatus 均有映射）"""
    mapping = get_contract_mapping()
    try:
        return mapping.issue_to_generic[IssueStatus(status).value]
    except (KeyError, ValueError) as e:
        raise ValueError(f"未知 IssueStatus: {status!r}") from e


def generic_status_to_issue(status: str) -> str:
    """通用状态 → IssueStatus（规范逆映射；未知值抛 ValueError → 422）"""
    mapping = get_contract_mapping()
    try:
        return mapping.generic_to_issue[status]
    except KeyError as e:
        raise ValueError(
            f"未知通用状态: {status!r}，可选值: {sorted(mapping.generic_to_issue)}"
        ) from e


def generic_status_to_issue_set(status: str) -> frozenset:
    """通用状态 → 全部正映射到它的 IssueStatus 集合（列表过滤语义）

    ?status=done 必须命中所有正映射为 done 的 IssueStatus（默认表
    resolved 与 closed 都显示为 done）；单值逆映射只取规范代表
    （resolved），按它过滤会漏掉 closed 的数据。
    未知值抛 ValueError（与 generic_status_to_issue 一致）。
    """
    mapping = get_contract_mapping()
    if status not in mapping.generic_to_issue:
        raise ValueError(
            f"未知通用状态: {status!r}，可选值: {sorted(mapping.generic_to_issue)}"
        )
    return frozenset(
        issue_status
        for issue_status, generic in mapping.issue_to_generic.items()
        if generic == status
    )


def normalize_label(label: str) -> str:
    """标签规范化：去首尾空白；空串/超长直接拒绝（Tag.name 为 String(100)）"""
    normalized = label.strip() if isinstance(label, str) else ""
    if not normalized:
        raise ValueError("标签不能为空")
    if len(normalized) > 100:
        raise ValueError(f"标签过长（最大 100 字符）: {normalized[:20]}...")
    return normalized


def normalize_updated_since(value: datetime) -> datetime:
    """updated_since 游标归一化：tz-aware → naive UTC（DB 侧为 naive UTC 时间戳）"""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def build_issue_url(issue_id: str) -> str:
    """契约 url 字段：OpenTask 前端详情页相对链接（Orca 侧拼接 base URL）"""
    return f"{ISSUE_DETAIL_PATH}?id={issue_id}"
