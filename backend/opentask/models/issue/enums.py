"""Issue 相关枚举定义"""
from enum import Enum


class IssueType(str, Enum):
    """Issue 类型"""
    BUG = "bug"                      # Bug - 程序错误
    FEATURE = "feature"              # Feature - 新功能请求
    QUESTION = "question"            # Question - 问题咨询
    FEEDBACK = "feedback"            # Feedback - 用户反馈
    INCIDENT = "incident"            # Incident - 突发事件
    IMPROVEMENT = "improvement"      # Improvement - 改进建议


class IssueStatus(str, Enum):
    """Issue 状态"""
    OPEN = "open"                    # 待处理
    IN_PROGRESS = "in_progress"      # 进行中
    FEEDBACK = "feedback"            # 等待反馈
    RESOLVED = "resolved"            # 已解决
    CLOSED = "closed"                # 已关闭
    REJECTED = "rejected"            # 已拒绝


class IssuePriority(str, Enum):
    """Issue 优先级"""
    LOW = "low"                      # 低
    MEDIUM = "medium"                # 中
    HIGH = "high"                    # 高
    CRITICAL = "critical"            # 紧急


class CommentType(str, Enum):
    """评论类型"""
    COMMENT = "comment"              # 普通评论
    SYSTEM = "system"                # 系统消息
    STATUS_CHANGE = "status_change"  # 状态变更
    ASSIGNMENT = "assignment"        # 分配变更
    PRIORITY_CHANGE = "priority_change"  # 优先级变更


class RelationType(str, Enum):
    """Issue 关系类型"""
    BLOCKS = "blocks"                        # 阻塞
    IS_BLOCKED_BY = "is_blocked_by"          # 被阻塞
    RELATES_TO = "relates_to"                # 关联
    DUPLICATES = "duplicates"                # 重复
    IS_DUPLICATED_BY = "is_duplicated_by"    # 被重复
    DEPENDS_ON = "depends_on"                # 依赖
    IS_DEPENDED_BY = "is_depended_by"        # 被依赖


class TimelineAction(str, Enum):
    """时间线动作类型"""
    CREATED = "created"                      # 创建
    UPDATED = "updated"                      # 更新
    COMMENTED = "commented"                  # 评论
    STATUS_CHANGED = "status_changed"        # 状态变更
    ASSIGNED = "assigned"                    # 分配
    PRIORITY_CHANGED = "priority_changed"    # 优先级变更
    DUE_DATE_CHANGED = "due_date_changed"    # 截止日期变更
    RELATION_ADDED = "relation_added"        # 添加关系
    RELATION_REMOVED = "relation_removed"    # 移除关系
    ATTACHMENT_ADDED = "attachment_added"    # 添加附件
    ATTACHMENT_REMOVED = "attachment_removed"  # 移除附件
    LABEL_ADDED = "label_added"              # 添加标签
    LABEL_REMOVED = "label_removed"          # 移除标签
    REACTION_ADDED = "reaction_added"        # 添加反应
    REACTION_REMOVED = "reaction_removed"    # 移除反应
    RESOLVED = "resolved"                    # 已解决
    CLOSED = "closed"                        # 已关闭
    REOPENED = "reopened"                    # 重新打开
    CUSTOM_FIELD_CHANGED = "custom_field_changed"  # E41：自定义字段变更
    CYCLE_CHANGED = "cycle_changed"              # E41：Cycle 变更
    ESTIMATE_CHANGED = "estimate_changed"        # E41：估分变更
    PROJECT_CHANGED = "project_changed"          # E41：项目变更
    SLA_PAUSED = "sla_paused"                    # E48：SLA 暂停
    SLA_RESUMED = "sla_resumed"                  # E48：SLA 恢复
