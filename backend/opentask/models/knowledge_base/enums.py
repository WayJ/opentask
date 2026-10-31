"""知识库枚举定义"""
from enum import Enum


class KnowledgeBaseStatus(str, Enum):
    """知识库状态"""

    ACTIVE = "active"
    ARCHIVED = "archived"

    @classmethod
    def values(cls) -> list[str]:
        """获取所有枚举值"""
        return [item.value for item in cls]
