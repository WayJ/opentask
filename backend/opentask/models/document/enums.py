"""文档模块枚举定义 - 简化的附件模型"""
from enum import Enum


class DocumentStatus(str, Enum):
    """文档状态"""
    DRAFT = "DRAFT"           # 草稿
    PUBLISHED = "PUBLISHED"   # 已发布
    ARCHIVED = "ARCHIVED"     # 已归档
