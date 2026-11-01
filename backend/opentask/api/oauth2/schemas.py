"""OAuth2 API 请求/响应模型

请求/响应形状对齐 RFC 6749（授权码流程）与 RFC 7009（吊销）：
- token 端点成功体：``{access_token, token_type, expires_in, refresh_token, scope}``；
- token 端点错误体：``{error, error_description}``（HTTP 400 / 401）。

注意：token 端点**不走** ``utils.response.success_response`` 包装——OAuth2
消费者按 RFC 6749 §5 解析 body，包一层会破坏互操作性。
"""

from typing import Optional

from pydantic import BaseModel, Field


# ===== client 注册管理 =====


class OAuthClientCreate(BaseModel):
    """注册 OAuth client"""

    client_id: str = Field(..., min_length=1, max_length=64, description="客户端公开标识")
    name: str = Field(..., min_length=1, max_length=255, description="应用名称（同意页展示）")
    description: Optional[str] = Field(None, description="应用描述（同意页展示）")
    redirect_uris: list[str] = Field(..., min_length=1, description="回调地址白名单")
    scopes: list[str] = Field(default_factory=list, description="允许的 scope 集合")
    grant_types: Optional[list[str]] = Field(
        None, description="允许的授权类型；默认 authorization_code + refresh_token"
    )


class OAuthClientUpdate(BaseModel):
    """更新 OAuth client 元信息"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    redirect_uris: Optional[list[str]] = None
    scopes: Optional[list[str]] = None
    status: Optional[str] = Field(None, description="ACTIVE / DISABLED")


class OAuthClientView(BaseModel):
    """client 视图（**不含 secret 明文**）"""

    client_id: str
    name: str
    description: Optional[str] = None
    redirect_uris: list[str]
    scopes: list[str]
    grant_types: list[str]
    status: str
    secret_prefix: str
    created_at: str


class OAuthClientCreated(BaseModel):
    """注册/轮换 secret 的响应（**secret 明文仅此一次**）"""

    client: OAuthClientView
    client_secret: str = Field(..., description="客户端密钥明文——仅此一次返回，请立即保存")


# ===== 授权请求 =====


class AuthorizeContextRequest(BaseModel):
    """授权请求参数（SPA 同意页提交）"""

    client_id: str
    redirect_uri: str
    response_type: str = "code"
    scope: str = ""
    state: Optional[str] = None


class AuthorizeContextView(BaseModel):
    """同意页展示上下文"""

    client_id: str
    client_name: str
    client_description: Optional[str] = None
    scope: list[str]
    redirect_uri: str
    redirect_host: str
    state: Optional[str] = None


class AuthorizeDecisionRequest(BaseModel):
    """同意/拒绝决策"""

    client_id: str
    redirect_uri: str
    scope: str = ""
    state: Optional[str] = None
    decision: str = Field(..., description="approve / deny")


class AuthorizeDecisionResponse(BaseModel):
    """决策结果——前端据此跳转"""

    redirect_to: str = Field(..., description="应跳转的完整 URL（含 code 或 error 与 state）")


# ===== token 端点（RFC 6749 §5） =====


class OAuthTokenResponse(BaseModel):
    """token 端点成功响应"""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class OAuthErrorResponse(BaseModel):
    """token 端点错误响应（RFC 6749 §5.2）"""

    error: str
    error_description: Optional[str] = None


# ===== userinfo =====


class OAuthUserInfo(BaseModel):
    """用户信息端点响应"""

    sub: str
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None


# ===== revoke（RFC 7009） =====


class OAuthRevokeRequest(BaseModel):
    """吊销请求"""

    token: str
    client_id: str
    client_secret: str
