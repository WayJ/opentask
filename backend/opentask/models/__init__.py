from opentask.models.base import DBModel
from opentask.models.conversation.model import ConversationModel
from opentask.models.media.model import MediaModel
from opentask.models.message.model import MessageModel
from opentask.models.user.model import UserModel

from opentask.models.task.model import Task
from opentask.models.requirement.model import (
    Requirement,
    Event,
    Project,
    RepoConfig,
    RequirementRepo,
    Comment,
    QueueJob,
)
from opentask.models.knowledge.model import Knowledge
from opentask.models.knowledge_base.model import KnowledgeBase
from opentask.models.knowledge_category.model import KnowledgeCategory
from opentask.models.mission_center.model import AgentTask, AgentWallet, AgentTransaction
from opentask.models.user_center import (
    Department,
    Position,
    UserDept,
    Role,
    Permission,
    RolePermission,
    UserRole,
    RoleDept,
    RefreshToken,
)
from opentask.models.agent import Agent

# 补齐未自动注册的模型模块：确保 `from opentask.models import *` / alembic
# autogenerate 拿到完整 metadata（此前 conftest 需手工 import Tag 同理）
from opentask.models.tag import Tag
from opentask.models.issue import (
    Issue,
    IssueComment,
    IssueRelation,
    IssueTimeline,
    IssueTag,
    IssueReaction,
)
from opentask.models.issue_collection import IssueCollection
from opentask.models.workspace import Workspace, WorkspaceMember
from opentask.models.notification import Notification
from opentask.models.oauth2 import (
    OAuthAccessToken,
    OAuthAuthorizationCode,
    OAuthClient,
    OAuthRefreshToken,
)
from opentask.models.work_management import (
    RdGroup,
    RdGroupMember,
    CostProject,
    WorkAssignment,
    WorkFeedback,
    WorkAssignmentAttachment,
)

__all__ = [
    "DBModel",
    "ConversationModel",
    "MediaModel",
    "MessageModel",
    "UserModel",

    "Task",
    "Requirement",
    "Event",
    "Project",
    "RepoConfig",
    "RequirementRepo",
    "Comment",
    "QueueJob",
    "Knowledge",
    "KnowledgeBase",
    "KnowledgeCategory",
    "AgentTask",
    "AgentWallet",
    "AgentTransaction",
    "Department",
    "Position",
    "UserDept",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "RoleDept",
    "RefreshToken",
    "Agent",
    "Tag",
    "Issue",
    "IssueComment",
    "IssueRelation",
    "IssueTimeline",
    "IssueTag",
    "IssueReaction",
    "IssueCollection",
    "Workspace",
    "WorkspaceMember",
    "Notification",
    "OAuthClient",
    "OAuthAuthorizationCode",
    "OAuthAccessToken",
    "OAuthRefreshToken",
    "RdGroup",
    "RdGroupMember",
    "CostProject",
    "WorkAssignment",
    "WorkFeedback",
    "WorkAssignmentAttachment",
]
