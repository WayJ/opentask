"""知识枚举定义"""
from enum import Enum


class KnowledgeStatus(str, Enum):
    """知识状态"""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    @classmethod
    def values(cls) -> list[str]:
        """获取所有枚举值"""
        return [item.value for item in cls]


class KnowledgeVisibility(str, Enum):
    """知识可见性"""

    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"

    @classmethod
    def values(cls) -> list[str]:
        """获取所有枚举值"""
        return [item.value for item in cls]
