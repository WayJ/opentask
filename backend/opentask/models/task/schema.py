"""任务模块 Pydantic Schema"""
from datetime import datetime
from typing import Optional, Any
from enum import Enum
from pydantic import Field, BaseModel, field_validator

from .enums import TaskType, TaskStatus, TaskFramework


# ============================================================================
# 设计文档摘要 Schema（用于嵌入到任务响应中）
# ============================================================================


class DocumentSummary(BaseModel):
    """文档摘要（用于嵌入到任务响应中）"""
    id: str
    title: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    """任务基础 Schema"""
    title: str = Field(..., description="任务标题", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="任务描述")
    task_type: TaskType = Field(TaskType.IMPLEMENT, description="任务类型")
    assigned_to: Optional[str] = Field(None, description="分配给谁")
    input_data: Optional[dict] = Field(None, description="任务输入参数")
    code: Optional[str] = Field(None, description="任务编码 (如 1, 1.1, 2.1)")


class TaskCreate(TaskBase):
    """创建任务 Schema"""
    requirement_id: str = Field(..., description="所属需求 ID")
    parent_id: Optional[str] = Field(None, description="父任务 ID (可选，用于创建子任务)")
    depends_on: Optional[list[str]] = Field(None, description="依赖的任务 ID 列表")
    framework: Optional[TaskFramework] = Field(None, description="任务框架（如 PGE）")


class TaskUpdate(BaseModel):
    """更新任务 Schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    assigned_to: Optional[str] = None
    parent_id: Optional[str] = Field(None, description="父任务 ID (可选)")
    output_data: Optional[dict] = None
    artifacts: Optional[dict] = None
    error_message: Optional[str] = None


class TaskResponse(TaskBase):
    """任务响应 Schema"""
    id: str
    requirement_id: str
    parent_id: Optional[str] = Field(None, description="父任务 ID")
    code: Optional[str] = Field(None, description="任务编码 (如 1, 1.1, 2.1)")
    agent_task_id: Optional[str] = Field(None, description="关联的 Mission Center 任务 ID")
    status: TaskStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    input_data: Optional[dict]
    output_data: Optional[dict]
    artifacts: Optional[dict]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime

    # 子任务列表（仅一级子任务）
    children: list["TaskResponse"] = Field(default_factory=list, description="子任务列表")

    # 依赖的任务
    dependencies: list[str] = Field(default_factory=list)
    dependents: list[str] = Field(default_factory=list)

    # 关联文档（轻量级摘要）
    documents: list[DocumentSummary] = Field(default_factory=list, description="关联的设计文档")

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应 Schema"""
    data: list[TaskResponse]
    total: int
    page: int
    page_size: int


class TaskDependencyCreate(BaseModel):
    """创建任务依赖 Schema"""
    task_id: str
    depends_on_id: str
    dependency_type: str = Field("hard", description="依赖类型: hard(必须) / soft(建议)")


class TaskImportItem(BaseModel):
    """单个导入任务 Schema (支持 task.json 格式)"""
    id: Optional[int] = Field(None, description="原始任务 ID (可选)")
    title: str = Field(..., description="任务标题", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="任务描述")
    steps: Optional[list[str]] = Field(None, description="任务步骤列表")
    controller: Optional[str] = Field(None, description="关联的 Controller")
    path: Optional[str] = Field(None, description="文件路径")
    status: Optional[str] = Field(None, description="状态 (pending/in_progress/completed/failed)")
    passes: Optional[bool] = Field(None, description="是否通过测试")
    task_type: TaskType = Field(TaskType.IMPLEMENT, description="OpenTask 任务类型")
    depends_on: Optional[list[int]] = Field(None, description="依赖的任务 ID 列表 (原始 ID)")


class TaskImportData(BaseModel):
    """批量导入任务数据 Schema"""
    project: str = Field(..., description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    tasks: list[TaskImportItem] = Field(..., description="任务列表")


class TaskImportResponse(BaseModel):
    """批量导入响应 Schema"""
    requirement_id: str
    imported_count: int
    skipped_count: int
    failed_count: int
    tasks: list[TaskResponse]
    errors: list[str] = Field(default_factory=list)


# ============================================================================
# PGE 任务相关 Schema
# ============================================================================


class SuperpowerSkill(str, Enum):
    """Superpower Skill 枚举"""
    BRAINSTORMING = "superpowers:brainstorming"
    WRITING_PLANS = "superpowers:writing-plans"
    TEST_DRIVEN_DEVELOPMENT = "superpowers:test-driven-development"
    EXECUTING_PLANS = "superpowers:executing-plans"
    SYSTEMATIC_DEBUGGING = "superpowers:systematic-debugging"
    CODE_REVIEW = "superpowers:code-review"
    VERIFICATION_BEFORE_COMPLETION = "superpowers:verification-before-completion"
    FRONTEND_DESIGN = "superpowers:frontend-design"


# Superpower Skills 定义（用于前端展示）
SUPERPOWER_SKILLS = {
    "规划类": [
        {
            "id": "superpowers:brainstorming",
            "name": "创意风暴",
            "description": "在创意工作前使用，强制发散思维，探索多种可能性"
        },
        {
            "id": "superpowers:writing-plans",
            "name": "编写计划",
            "description": "将需求分解为可执行的任务清单和实施步骤"
        },
    ],
    "执行类": [
        {
            "id": "superpowers:test-driven-development",
            "name": "测试驱动开发",
            "description": "在编写实现代码前先写测试，确保代码质量"
        },
        {
            "id": "superpowers:executing-plans",
            "name": "执行计划",
            "description": "按照既定计划执行任务，跟踪进度"
        },
        {
            "id": "superpowers:systematic-debugging",
            "name": "系统化调试",
            "description": "遇到 bug 时系统性排查，而非猜测式修改"
        },
    ],
    "审查类": [
        {
            "id": "superpowers:code-review",
            "name": "代码审查",
            "description": "完成任务后审查代码，确保符合规范"
        },
        {
            "id": "superpowers:verification-before-completion",
            "name": "完成前验证",
            "description": "标记完成前进行最终验证，确保所有检查项通过"
        },
    ],
    "设计类": [
        {
            "id": "superpowers:frontend-design",
            "name": "前端设计",
            "description": "创建前端界面时使用，确保 UI/UX 质量"
        },
    ],
}


class PGETaskCreate(BaseModel):
    """创建 PGE 任务请求 Schema"""
    requirement_id: str = Field(..., description="所属需求 ID")
    title: str = Field(..., min_length=1, max_length=255, description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    framework: TaskFramework = Field(TaskFramework.PGE, description="任务框架")
    required_skills: list[str] = Field(
        default_factory=list,
        description="必需的 Superpower Skills"
    )


class TaskPromptResponse(BaseModel):
    """任务提示词响应 Schema"""
    task_id: str
    prompt: str = Field(..., description="结构化的任务提示词（Markdown 格式）")
