"""任务数据模型"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON

from opentask.models.base import DBModel
from .enums import TaskType, TaskStatus


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


class Task(DBModel):
    """任务模型 - 支持父子层级结构"""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    requirement_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # 父任务ID，支持任务层级结构（子任务）
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # 任务编码 (如 1, 1.1, 2.1)
    code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="任务编码 (如 1, 1.1, 2.1)"
    )

    # 关联的 Mission Center 任务 ID
    agent_task_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="关联的 Mission Center 任务 ID"
    )

    # 基本信息
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, insert_default="IMPLEMENT")

    # 任务框架（PGE、PARALLEL 等）
    framework: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="任务框架（如 PGE）"
    )

    # 必需的 Superpower Skills
    required_skills: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="必需的 Superpower Skills"
    )

    # 状态管理
    status: Mapped[str] = mapped_column(String(50), nullable=False, insert_default="PENDING")

    # 执行信息
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 分配给谁(AI Agent 或用户)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 任务输入输出
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 任务输入参数
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 任务输出结果
    artifacts: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 产物(Git commit、PR、测试报告等)

    # 错误信息
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=0)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # 部门归属快照
    dept_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("department.id"),
        nullable=True,
        index=True,
        comment="部门归属快照（创建时所属部门）"
    )

    # 关系
    # 父任务关系
    parent = relationship(
        "Task",
        remote_side=[id],
        back_populates="children"
    )
    # 子任务关系
    children = relationship(
        "Task",
        back_populates="parent",
        foreign_keys=[parent_id],
        order_by="Task.code.asc()"
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, code={self.code}, title={self.title}, status={self.status})>"

    __table_args__ = (
        Index("idx_tasks_parent_id", "parent_id"),
        Index("idx_tasks_requirement_id", "requirement_id"),
        Index("idx_tasks_code", "code"),
        Index("idx_tasks_requirement_code", "requirement_id", "code"),
    )


class TaskDependency(DBModel):
    """任务依赖关系模型 (DAG)"""
    __tablename__ = "task_dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    depends_on_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 依赖类型
    dependency_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        insert_default="hard"  # hard: 必须等待完成, soft: 建议等待
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<TaskDependency(task_id={self.task_id}, depends_on={self.depends_on_id})>"
