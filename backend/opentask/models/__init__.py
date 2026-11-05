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
from opentask.models.tag import Tag, TagGroup
from opentask.models.issue import (
    Issue,
    IssueComment,
    IssueRelation,
    IssueTimeline,
    IssueTag,
    IssueReaction,
    CommentReaction,
)
from opentask.models.notification_preference import NotificationPreference
from opentask.models.issue_collection import IssueCollection
from opentask.models.workspace import Workspace, WorkspaceMember, WorkspaceInvite
from opentask.models.notification import Notification
from opentask.models.issue_template import IssueTemplate
from opentask.models.project_template import ProjectTemplate
from opentask.models.initiative import Initiative, InitiativeProject, InitiativeRelation
from opentask.models.entity_document import EntityDocument
from opentask.models.issue_vcs_link import IssueVcsLink
from opentask.models.issue_saved_view import IssueSavedView
from opentask.models.issue_display_prefs import IssueDisplayPrefs
from opentask.models.cycle import Cycle
from opentask.models.milestone import Milestone
from opentask.models.project_health import ProjectHealthUpdate
from opentask.models.project_watcher import ProjectWatcher
from opentask.models.issue_watcher import IssueWatcher
from opentask.models.issue_assignee import IssueAssignee
from opentask.models.activity_read_cursor import ActivityReadCursor
from opentask.models.favorite import Favorite
from opentask.models.customer import Customer, CustomerRequest, CustomerRequestIssue, CustomerRequestPublicReply
from opentask.models.custom_field import CustomField, IssueCustomFieldValue, IssueFormulaCache
from opentask.models.automation import AutomationRule, AutomationPendingAction
from opentask.models.workspace_webhook import WorkspaceWebhook, WebhookDeliveryLog
from opentask.models.issue_form import IssueForm
from opentask.models.issue_recurrence import IssueRecurrence
from opentask.models.due_reminder_delivery import DueReminderDelivery
from opentask.models.webhook_alert_delivery import WebhookAlertDelivery
from opentask.models.insights_saved_report import InsightsSavedReport
from opentask.models.insights_digest_delivery import InsightsDigestDelivery
from opentask.models.sla import SlaPolicy, IssueSlaClock
from opentask.models.access_token import AccessToken
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
    "TagGroup",
    "Issue",
    "IssueComment",
    "IssueRelation",
    "IssueTimeline",
    "IssueTag",
    "IssueReaction",
    "IssueCollection",
    "Workspace",
    "WorkspaceMember",
    "WorkspaceInvite",
    "Notification",
    "IssueSavedView",
    "IssueDisplayPrefs",
    "Cycle",
    "Milestone",
    "ProjectTemplate",
    "ProjectHealthUpdate",
    "ProjectWatcher",
    "IssueWatcher",
    "IssueAssignee",
    "ActivityReadCursor",
    "Favorite",
    "Customer",
    "CustomerRequest",
    "CustomerRequestIssue",
    "CustomerRequestPublicReply",
    "CustomField",
    "IssueCustomFieldValue",
    "IssueFormulaCache",
    "AutomationRule",
    "AutomationPendingAction",
    "WorkspaceWebhook",
    "WebhookDeliveryLog",
    "IssueForm",
    "IssueRecurrence",
    "DueReminderDelivery",
    "WebhookAlertDelivery",
    "InsightsSavedReport",
    "InsightsDigestDelivery",
    "SlaPolicy",
    "IssueSlaClock",
    "CommentReaction",
    "NotificationPreference",
    "AccessToken",
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
