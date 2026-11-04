import logging
from typing import Any, AsyncContextManager, Callable, Mapping
from typing_extensions import Self

import fastapi
from fastapi import Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from opentask.api.auth.router import router as auth_router
from opentask.api.conversation.router import router as conversation_router
from opentask.api.settings.router import router as settings_router
from opentask.api.agent.router import router as agent_router
from opentask.api.requirement.router import router as requirement_router
from opentask.api.project.router import router as project_router
from opentask.api.workspace import router as workspace_router
from opentask.api.inbox import router as inbox_router
from opentask.api.saved_views import router as saved_views_router
from opentask.api.display_prefs import router as display_prefs_router
from opentask.api.cycles import router as cycles_router
from opentask.api.favorites import router as favorites_router
from opentask.api.triage import router as triage_router
from opentask.api.issue_templates import router as issue_templates_router
from opentask.api.invites import router as invites_router
from opentask.api.tags.router import tags_router, groups_router as tag_groups_router
# from opentask.api.ai.router import router as ai_router  # 模块不存在，已注释
from opentask.api.mission_center import router as mission_center_router
from opentask.api.agent.routes import router as agent_management_router
from opentask.api.access_token import router as access_token_router
from opentask.api.repo import router as repo_router
from opentask.api.knowledge_base.router import router as knowledge_base_router
from opentask.api.knowledge.router import router as knowledge_router
from opentask.api.knowledge_category.router import router as knowledge_category_router
from opentask.api.issue.router import router as issue_router
from opentask.api.tasks import router as tasks_contract_router
from opentask.api.oauth2 import router as oauth2_router
from opentask.api.oauth2 import read_router as oauth2_read_router
from opentask.api.attachment.router import router as attachment_router
from opentask.api.knowledge.webhooks import router as webhook_router
from opentask.api.user.router import router as user_router
from opentask.api.user_center.router import router as user_center_router
from opentask.api.user_center.dept_router import router as dept_router
from opentask.api.user_center.role_router import router as role_router
from opentask.api.user_center.perm_router import router as perm_router
from opentask.api.user_center.dingtalk_router import router as dingtalk_router
from opentask.api.websocket import router as websocket_router
from opentask.api.test.mission_center_routes import router as test_mission_center_router
from opentask.api.task import router as task_router
from opentask.api.dashboard.router import router as dashboard_router
from opentask.auth import authenticate
from opentask.config import config
from opentask.errors import UserFacingError, ValidationError
from opentask.middleware.sso_auth import SsoAuthMiddleware
from opentask.repositories.base import NotFoundError, NotUniqueError

logger = logging.getLogger(__name__)


def handle_exceptions(request: Request, e: Exception) -> JSONResponse:
    if isinstance(e, NotFoundError):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": e.message})
    elif isinstance(e, NotUniqueError):
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": e.message})
    elif isinstance(e, ValidationError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(e)})
    elif isinstance(e, UserFacingError):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(e)})

    logger.exception(e)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(e)})


class App(fastapi.FastAPI):
    def __init__(  # type: ignore[misc]
        self,
        lifespan: Callable[[Self], AsyncContextManager[Mapping[str, Any]]] | None = None,
    ) -> None:
        super().__init__(title="OpenTask API", lifespan=lifespan)
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"], # 不限制跨域
            allow_credentials=False, # JWT认证不需要credentials
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # SSO 认证中间件已禁用 - 使用 opentask JWT 认证代替
        # 用户通过 /api/auth/login 登录后获得 opentask JWT token
        # self.add_middleware(SsoAuthMiddleware)

        # 始终启用认证，使用数据库用户系统
        common_dependencies = [Depends(authenticate)]

        # Add route for login (无需认证)
        self.include_router(auth_router)
        # Add OAuth compatible route for frontend (无需认证)
        # self.include_router(oauth_router)
        # Add webhook routes (无需认证，由 GitLab/GitHub 调用)
        self.include_router(webhook_router)

        # Workspace routes (需要认证)
        self.include_router(settings_router, dependencies=common_dependencies)
        self.include_router(conversation_router, dependencies=common_dependencies)
        self.include_router(workspace_router)
        self.include_router(inbox_router)
        self.include_router(saved_views_router)
        self.include_router(display_prefs_router)
        self.include_router(cycles_router)
        self.include_router(favorites_router)
        self.include_router(triage_router)
        self.include_router(issue_templates_router)
        self.include_router(invites_router)
        self.include_router(tags_router)
        self.include_router(tag_groups_router)
        self.include_router(agent_router, dependencies=common_dependencies)
        # Requirement routes (需要认证)
        self.include_router(requirement_router, dependencies=common_dependencies)
        # Task routes (需要认证)
        self.include_router(task_router, dependencies=common_dependencies)
        # Dashboard routes (需要认证)
        self.include_router(dashboard_router, dependencies=common_dependencies)
        # Project routes (需要认证)
        self.include_router(project_router, dependencies=common_dependencies)
        # Mission Center routes (需要认证)
        self.include_router(mission_center_router, dependencies=common_dependencies)
        # Agent Management routes (需要认证)
        self.include_router(agent_management_router, dependencies=common_dependencies)
        # Access Token routes (需要认证)
        self.include_router(access_token_router, dependencies=common_dependencies)
        # Repository routes (需要认证)
        self.include_router(repo_router, dependencies=common_dependencies)
        # # AI routes (需要认证) - 模块不存在，已注释
        # self.include_router(ai_router, dependencies=common_dependencies)
        # Knowledge Base routes (需要认证)
        self.include_router(knowledge_base_router, dependencies=common_dependencies)
        # Knowledge routes (需要认证)
        self.include_router(knowledge_router, dependencies=common_dependencies)
        # Knowledge Category routes (需要认证)
        self.include_router(knowledge_category_router, dependencies=common_dependencies)
        # Issue routes (需要认证)
        # Issue Collection routes 已合并到 issue_router
        self.include_router(issue_router, dependencies=common_dependencies)
        # Task Source Contract routes (Orca 通用任务契约，D7 与 issue API 并列；
        # 挂根 /tasks + /capabilities，D12/S5。鉴权走契约层 authenticate_contract
        # （API Key + client credentials，401 独立语义带错误码字段；/tasks/token
        # 与 /capabilities 公开），不叠全局 authenticate——其缺头时是 HTTPBearer
        # 的 403 "Not authenticated"，与契约层 401 语义冲突)
        self.include_router(tasks_contract_router)
        # OAuth2 Provider 路由（自建授权服务器，spec: docs/superpowers/specs/
        # 2026-11-02-oauth2-provider-design.md）：
        # - /oauth2/token、/oauth2/userinfo、/oauth2/revoke 是标准协议端点，
        #   消费者服务端直连，鉴权走各自的 client 凭证 / Bearer 校验；
        # - /api/oauth2/* 是 SPA 授权入口的配套与 client 注册管理，各自带
        #   authenticate（会话）或 admin 守卫；
        # - **不叠全局 common_dependencies**：OAuth 层有自己的鉴权语义，
        #   叠加会让缺头时的错误体与 OAuth2 协议形状冲突。
        self.include_router(oauth2_router)
        # OAuth2 只读数据面（scope 守卫：read:tasks / read:projects /
        # read:requirements / profile）
        self.include_router(oauth2_read_router)
        # Attachment routes (公共访问，无需认证)
        self.include_router(attachment_router, dependencies=[])
        # Git routes (需要认证) - TODO: 依赖已删除的 file_storage 等模块，暂时注释
        # self.include_router(git_router, dependencies=common_dependencies)

        # User management routes (需要认证)
        # 认证在路由函数内部处理，不使用 common_dependencies
        self.include_router(user_router)

        # User Center migrate routes (需要认证)
        # 认证在路由函数内部处理，不使用 common_dependencies
        self.include_router(user_center_router)

        # 部门管理 routes (需要认证)
        # 认证在路由函数内部处理（写操作另挂 require_permission），不使用 common_dependencies
        self.include_router(dept_router)

        # 钉钉同步 routes (需要认证)
        # 认证与权限在路由函数内部处理（require_permission），不使用 common_dependencies
        self.include_router(dingtalk_router)

        # 角色管理 routes (需要认证)
        # 认证与权限在路由函数内部处理（require_permission），不使用 common_dependencies
        self.include_router(role_router)

        # 权限点管理 routes (需要认证)
        # 认证与权限在路由函数内部处理（require_permission），不使用 common_dependencies
        self.include_router(perm_router)

        # WebSocket Hub routes (无需认证 - 使用自己的认证机制)
        self.include_router(websocket_router)

        # 测试路由（无需认证）- 用于开发和测试
        self.include_router(test_mission_center_router)

        # Handle 500s separately to play well with TestClient and allow re-raising in tests
        self.add_exception_handler(NotFoundError, handle_exceptions)
        self.add_exception_handler(NotUniqueError, handle_exceptions)
        self.add_exception_handler(ValidationError, handle_exceptions)
        self.add_exception_handler(UserFacingError, handle_exceptions)
        self.add_exception_handler(Exception, handle_exceptions)
