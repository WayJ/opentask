import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_serializer
from pydantic.alias_generators import to_camel

logger = logging.getLogger(__name__)


# ===== 原有 Schema =====

class UserUpdateIn(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=250)

    openai_api_key: Optional[SecretStr] = Field(None, min_length=4)
    openai_base_url: str | None = Field(None, min_length=4)
    langsmith_api_key: Optional[SecretStr] = Field(None, min_length=4)
    preferred_openai_model: Optional[str] = None
    sentry_enabled: Optional[bool] = None
    analytics_enabled: Optional[bool] = None
    hide_sql_preference: Optional[bool] = None

    @field_serializer("openai_api_key")
    def dump_openai_api_key(self, v: SecretStr) -> str:
        return v.get_secret_value()

    @field_serializer("langsmith_api_key")
    def dump_langsmith_api_key(self, v: SecretStr | None) -> str | None:
        return v.get_secret_value() if v else None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    openai_api_key: Optional[SecretStr] = None
    openai_base_url: str | None = None
    langsmith_api_key: Optional[SecretStr] = None
    preferred_openai_model: Optional[str] = None
    sentry_enabled: bool
    analytics_enabled: Optional[bool] = None
    hide_sql_preference: Optional[bool] = None


class UserWithKeys(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None

    openai_api_key: SecretStr
    openai_base_url: str | None = None
    langsmith_api_key: SecretStr | None = None
    preferred_openai_model: str
    sentry_enabled: bool
    analytics_enabled: Optional[bool] = None
    hide_sql_preference: Optional[bool] = None


class AvatarOut(BaseModel):
    blob: str


# ===== JNPF 集成相关 Schema =====

class JnpfUserInfo(BaseModel):
    """JNPF 用户信息（从 JNPF CurrentUser 接口返回）"""
    userId: str
    userAccount: str
    userName: str
    headIcon: Optional[str] = None
    organizeId: Optional[str] = None
    organizeName: Optional[str] = None
    positionId: Optional[str] = None
    positionName: Optional[str] = None


# ===== 用户管理相关 Schema =====

class UserListItem(BaseModel):
    """用户列表项"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    username: Optional[str] = Field(None, alias="username")
    name: Optional[str] = Field(None, alias="name")
    role_codes: list[str] = Field(default_factory=list, alias="roleCodes")
    jnpf_user_id: Optional[str] = Field(None, alias="jnpfUserId")
    jnpf_account: Optional[str] = Field(None, alias="jnpfAccount")
    jnpf_name: Optional[str] = Field(None, alias="jnpfName")
    organize_name: Optional[str] = Field(None, alias="organizeName")
    position_name: Optional[str] = Field(None, alias="positionName")
    role: str = Field("viewer", alias="role")
    status: int = Field(1, alias="status")
    last_login_time: Optional[datetime] = Field(None, alias="lastLoginTime")
    sync_time: Optional[datetime] = Field(None, alias="syncTime")
    created_at: datetime = Field(..., alias="createdAt")


class CurrentUserResponse(BaseModel):
    """当前用户响应（包含权限信息）"""
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: str
    jnpf_user_id: Optional[str] = None
    dingtalk_user_id: Optional[str] = None
    jnpf_account: Optional[str] = None
    jnpf_name: Optional[str] = None
    organize_name: Optional[str] = None
    position_name: Optional[str] = None
    role: str = "viewer"
    status: int = 1
    permissions: list[str] = []


class UserStatusUpdate(BaseModel):
    """用户状态更新"""
    status: int = Field(..., ge=0, le=1, description="用户状态：0-禁用、1-启用")


class UserRoleUpdate(BaseModel):
    """用户角色更新"""
    role: str = Field(..., description="角色：admin、maintainer、developer、viewer")


class UserSearchParams(BaseModel):
    """用户搜索参数"""
    current: int = Field(1, ge=1, description="当前页码")
    pageSize: int = Field(10, ge=1, le=100, description="每页大小")
    status: Optional[int] = Field(None, ge=0, le=1, description="用户状态筛选")
    keyword: Optional[str] = Field(None, max_length=100, description="关键字搜索（账号、姓名）")
    role: Optional[str] = Field(None, description="角色筛选")


# ===== 角色相关 Schema =====

class RoleInfo(BaseModel):
    """角色信息"""
    value: str
    label: str
    description: str


class RoleListResponse(BaseModel):
    """角色列表响应"""
    roles: list[RoleInfo]
