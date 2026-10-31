"""工作管理模块枚举定义"""

from enum import Enum


class RdGroupStatus(str, Enum):
    """研发组状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class RdGroupRole(str, Enum):
    """研发组角色"""

    DIRECTOR = "director"  # 产品总监
    LEADER = "leader"  # 组长
    MEMBER = "member"  # 成员


class CostProjectStatus(str, Enum):
    """成本项目状态"""

    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class WorkStatus(str, Enum):
    """工作状态"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class QualityLevel(str, Enum):
    """质量等级"""

    HIGH = "high"
    LOW = "low"
    UNKNOWN = "unknown"


class RelatedType(str, Enum):
    """关联类型"""

    REQUIREMENT = "requirement"
    ISSUE = "issue"


class UnplannedType(str, Enum):
    """计划外类型"""

    ISSUE_CREATED = "issue_created"
    ISSUE_RESOLVED = "issue_resolved"
    REQ_CREATED = "req_created"
    REQ_COMPLETED = "req_completed"
    OTHER = "other"
