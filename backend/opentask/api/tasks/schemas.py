"""任务源契约 Schema（Orca 通用任务模型）

字段形状按 epic ADR D12 裁定：
- id/title/description/status/assignee/url/timestamps + 可扩展 metadata
- assignee 为字符串 user ID，展示名放 metadata.username
- labels 双向映射现有 tags 关联表

状态词表为本 sprint 的默认通用状态集（todo/in_progress/in_review/done/cancelled），
与 IssueStatus 的映射表见 mapping.py；可配置化留待 S5。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .mapping import GENERIC_STATUSES, generic_status_to_issue, normalize_label


class TaskCreate(BaseModel):
    """创建任务（契约侧输入）"""

    title: str = Field(..., min_length=1, max_length=255, description="标题")
    description: Optional[str] = Field(None, description="描述")
    status: Optional[str] = Field(
        None, description=f"通用状态，默认 todo；可选：{sorted(GENERIC_STATUSES)}"
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
