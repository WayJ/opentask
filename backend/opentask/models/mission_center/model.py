"""Agent Task 数据模型"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as ENUM

from opentask.models.base import DBModel


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


class AgentTask(DBModel):
    """Agent 任务模型"""
    __tablename__ = "agent_tasks"

    # 主键
    task_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        insert_default=generate_uuid,
        comment="任务 ID"
    )

    # 基本信息
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="任务标题"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="任务描述"
    )

    # 优先级
    priority: Mapped[str] = mapped_column(
        ENUM("low", "medium", "high", "urgent", name="agent_task_priority"),
        nullable=False,
        insert_default="medium",
        comment="优先级"
    )

    # 分配信息
    assignee: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="分配给哪个 Agent"
    )

    # 截止时间
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="截止时间"
    )

    # 元数据
    meta_data: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        comment="元数据"
    )

    # 🔗 关联数据
    link_data: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="关联数据列表，格式: ['issue:uuid', 'requirement:uuid']"
    )

    # 需求列表
    requirements: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="需求列表"
    )

    # 🎯 验收标准
    acceptance_criteria: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="验收标准"
    )

    # 🎯 金币奖励
    reward: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="金币奖励"
    )

    # 状态管理
    status: Mapped[str] = mapped_column(
        ENUM("pending", "assigned", "in_progress", "completed", "failed", "cancelled", "blocked",
             name="agent_task_status"),
        nullable=False,
        insert_default="pending",
        index=True,
        comment="任务状态"
    )

    # 进度信息
    progress_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="进度百分比 (0-100)"
    )
    current_step: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        comment="当前步骤描述"
    )

    # 执行结果
    result: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="执行结果"
    )
    error: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="错误信息"
    )

    # 日志
    logs: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="日志列表"
    )

    # 🔥 进度历史记录
    progress_history: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="进度历史记录"
    )

    # 执行统计
    execution_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="执行时间（毫秒）"
    )

    # 时间跟踪
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        index=True,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
        comment="更新时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="完成时间"
    )

    # 部门归属快照
    dept_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("department.id"),
        nullable=True,
        index=True,
        comment="部门归属快照（创建时所属部门）"
    )

    # 索引
    __table_args__ = (
        Index("idx_agent_tasks_status", "status"),
        Index("idx_agent_tasks_priority", "priority"),
        Index("idx_agent_tasks_assignee", "assignee"),
        Index("idx_agent_tasks_status_priority", "status", "priority"),
        Index("idx_agent_tasks_assignee_status", "assignee", "status"),
    )

    # 关系
    comments: Mapped[List["AgentTaskComment"]] = relationship(
        "AgentTaskComment",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="select"
    )


class AgentWallet(DBModel):
    """Agent 钱包模型"""
    __tablename__ = "agent_wallets"

    # 主键
    agent_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="Agent ID"
    )

    # 余额信息
    balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="当前余额（金币）"
    )
    total_earned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="累计获得金币"
    )
    total_spent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="累计消费金币"
    )

    # 时间跟踪
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )

    # 索引
    __table_args__ = (
        Index("idx_agent_wallets_balance", "balance"),
    )


class AgentTransaction(DBModel):
    """Agent 交易流水模型"""
    __tablename__ = "agent_transactions"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        insert_default=generate_uuid,
        comment="交易 ID"
    )

    # 关联 Agent
    agent_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("agent_wallets.agent_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent ID"
    )

    # 交易信息
    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="交易金额（正数为收入，负数为支出）"
    )
    balance_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="交易后余额"
    )
    transaction_type: Mapped[str] = mapped_column(
        ENUM("task_reward", "task_penalty", "system_adjustment", "manual", name="transaction_type"),
        nullable=False,
        index=True,
        comment="交易类型"
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="交易描述"
    )

    # 关联任务
    related_task_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="关联任务 ID"
    )

    # 时间跟踪
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        index=True,
        comment="创建时间"
    )

    # 索引
    __table_args__ = (
        Index("idx_agent_transactions_agent", "agent_id"),
        Index("idx_agent_transactions_type", "transaction_type"),
        Index("idx_agent_transactions_task", "related_task_id"),
        Index("idx_agent_transactions_agent_created", "agent_id", "created_at"),
    )
