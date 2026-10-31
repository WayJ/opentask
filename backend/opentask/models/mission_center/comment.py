"""
Agent Task 评论数据模型
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from opentask.models.base import DBModel


class AgentTaskComment(DBModel):
    """任务评论模型"""
    __tablename__ = "agent_task_comments"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255), ForeignKey("agent_tasks.task_id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(255), nullable=True, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    content = Column(Text, nullable=False)
    comment_type = Column(String(50), nullable=False, default="comment")  # comment, claim, plan, question
    parent_id = Column(Integer, ForeignKey("agent_task_comments.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    task = relationship("AgentTask", back_populates="comments", foreign_keys=[task_id])
    parent = relationship("AgentTaskComment", remote_side=[id], foreign_keys=[parent_id])
    children = relationship("AgentTaskComment", remote_side=[parent_id], foreign_keys=[parent_id])

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "content": self.content,
            "comment_type": self.comment_type,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
