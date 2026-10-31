"""Agent 模型 - AI Agent 信息"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


class Agent(DBModel):
    """Agent 模型 - AI Agent 信息和生命周期管理"""

    __tablename__ = "agents"

    # 主键
    agent_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="Agent ID"
    )

    # 基本信息
    agent_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Agent 类型 (architecture|entertainment|coding)"
    )
    agent_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Agent 显示名称"
    )
    capabilities: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Agent 能力列表"
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="使用的 AI 模型"
    )

    # === 生命周期字段 ===

    # 状态字段
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        insert_default="registered",
        index=True,
        comment="Agent 状态 (registered|online|idle|busy|offline|retired|error)"
    )
    previous_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="上一个状态"
    )

    # 连接信息
    connected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="首次连接时间"
    )
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
        comment="最后心跳时间"
    )
    disconnected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="断开连接时间"
    )

    # 统计信息
    total_tasks_handled: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="总处理任务数"
    )
    successful_tasks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="成功任务数"
    )
    failed_tasks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="失败任务数"
    )
    total_execution_time: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="总执行时间（秒）"
    )

    # 当前任务
    current_task_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="当前正在处理的任务 ID"
    )
    current_task_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="当前任务开始时间"
    )

    # 健康监控
    heartbeat_misses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="心跳丢失次数"
    )
    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="错误次数"
    )
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="最后错误信息"
    )
    last_error_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="最后错误时间"
    )

    # 生命周期管理
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        insert_default=True,
        index=True,
        comment="是否激活"
    )
    retired_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="退役时间"
    )
    retired_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="退役操作者"
    )
    retire_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="退役原因"
    )

    # 元数据
    agent_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        comment="其他自定义信息"
    )

    # 时间戳
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
