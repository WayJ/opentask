"""任务源契约 Schema（Orca 通用任务模型）

字段形状按 epic ADR D12 裁定：
- id/title/description/status/assignee/url/timestamps + 可扩展 metadata
- assignee 为字符串 user ID，展示名放 metadata.username
- labels 双向映射现有 tags 关联表

状态词表经 contract.status_mapping 可配置（S5）：校验器运行时调用
mapping.generic_status_to_issue（随生效配置变化），无静态词表常量。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .mapping import generic_status_to_issue, normalize_label

# 契约版本号（GET /capabilities 下发；S6 OpenAPI spec 生成沿用）
CONTRACT_VERSION = "1.0"


class TaskCreate(BaseModel):
    """创建任务（契约侧输入）"""

    title: str = Field(..., min_length=1, max_length=255, description="标题")
    description: Optional[str] = Field(None, description="描述")
    status: Optional[str] = Field(
        None,
        description="通用状态，默认取映射表的 todo 侧；"
        "词表经 config contract.status_mapping 可配置，默认 "
        "todo/in_progress/in_review/done/cancelled",
    )
    assignee: Optional[str] = Field(None, description="负责人 user ID（字符串）")
    labels: Optional[List[str]] = Field(None, description="标签列表，映射到 OpenTask tags")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        generic_status_to_issue(v)  # 未词表内则抛 ValueError → 422
        return v

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        normalized = [normalize_label(x) for x in v]
        # 去重且保持顺序
        return list(dict.fromkeys(normalized))


class TaskUpdate(BaseModel):
    """更新任务（契约侧输入；仅更新出现的字段）"""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None  # 显式 null 表示取消分配
    labels: Optional[List[str]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        generic_status_to_issue(v)
        return v

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        normalized = [normalize_label(x) for x in v]
        return list(dict.fromkeys(normalized))


class ContractTask(BaseModel):
    """通用任务模型（契约侧输出）"""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="任务 ID（即 OpenTask Issue ID）")
    title: str
    description: Optional[str] = None
    status: str = Field(..., description="通用状态（经默认映射表转换）")
    assignee: Optional[str] = Field(None, description="负责人 user ID（字符串）")
    url: str = Field(..., description="OpenTask 前端详情页相对链接")
    labels: List[str] = Field(default_factory=list, description="标签（映射 tags）")
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="扩展元数据：issue_code/username/type/priority/reporter_id 等",
    )


class ContractTaskListResponse(BaseModel):
    """任务列表（分页 limit/offset + updated_since 游标）"""

    items: List[ContractTask]
    total: int = Field(..., description="过滤后的总数（不受 limit/offset 影响）")
    limit: int
    offset: int


class ContractCapabilities(BaseModel):
    """能力声明（GET /capabilities）：端点支持情况 + 契约版本 + 鉴权模式

    公开端点（无需凭证）：消费方（Orca 侧）对接前先探测能力再配置鉴权。
    """

    contract_version: str = Field(..., description="契约版本号")
    endpoints: Dict[str, str] = Field(
        ...,
        description="端点支持情况：能力名 → HTTP 方法与路径（不含即不支持）",
    )
    features: Dict[str, str] = Field(
        ...,
        description="特性说明：分页/增量游标/删除语义/状态映射来源（config|default）",
    )
    auth: Dict[str, Any] = Field(
        ...,
        description="鉴权模式：modes（bearer_api_key/oauth2_client_credentials）、"
        "token 端点、API Key 前缀",
    )
    status_vocabulary: List[str] = Field(
        ...,
        description="当前生效的通用状态词表（随 contract.status_mapping 配置变化）",
    )
