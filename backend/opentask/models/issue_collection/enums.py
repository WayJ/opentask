"""Issue Collection 相关枚举定义"""
from enum import Enum


class CollectionStatus(str, Enum):
    """问题集状态"""
    PENDING = "pending"          # 待拆解
    IN_PROGRESS = "in_progress"  # 拆解中
    COMPLETED = "completed"      # 已完成
