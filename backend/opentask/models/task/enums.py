"""任务模块枚举定义"""
from enum import Enum


class TaskFramework(str, Enum):
    """任务框架枚举"""
    PGE = "PGE"  # Plan-Generation-Evaluation

    # 未来扩展
    # PARALLEL = "PARALLEL"  # 多 Agent 并行

    def __str__(self) -> str:
        return self.value


class TaskType(str, Enum):
    """任务类型枚举"""
    DESIGN = "DESIGN"              # 设计任务(数据库、API、架构等)
    IMPLEMENT = "IMPLEMENT"        # 实现任务(编码)
    TEST = "TEST"                  # 测试任务
    REVIEW = "REVIEW"              # 代码审查
    DEPLOY = "DEPLOY"              # 部署任务
    DOCUMENT = "DOCUMENT"          # 文档任务
    RESEARCH = "RESEARCH"          # 研究任务

    # PGE 子任务类型
    PGE_PLAN = "PGE_PLAN"                     # 规划子任务
    PGE_GENERATION = "PGE_GENERATION"         # 生成子任务
    PGE_EVALUATION = "PGE_EVALUATION"         # 评估子任务

    def __str__(self) -> str:
        return self.value


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"            # 等待执行
    ASSIGNED = "ASSIGNED"          # 已分配
    RUNNING = "RUNNING"            # 执行中
    COMPLETED = "COMPLETED"        # 已完成
    FAILED = "FAILED"              # 失败
    BLOCKED = "BLOCKED"            # 阻塞
    CANCELLED = "CANCELLED"        # 已取消

    def __str__(self) -> str:
        return self.value
