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
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None
    resource: Optional[str] = None


class AuthorizeDecisionRequest(BaseModel):
    """同意/拒绝决策"""

    client_id: str
    redirect_uri: str
    scope: str = ""
    state: Optional[str] = None
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None
    resource: Optional[str] = None
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


# ===== 自动接入（Install Flow）=====


class InstallRequestCreate(BaseModel):
    """发起安装申请（未认证发起；滥用上限见契约 §5）

    ``code_challenge`` 为 PKCE S256：``BASE64URL(SHA256(verifier))``。
    OpenTask **从不接触 verifier**，只在兑换时用提交上来的 verifier 反算 challenge 比对。
    """

    client_id: str = Field(..., max_length=64, description="客户端公开标识")
    name: str = Field(..., max_length=255, description="应用名称")
    description: Optional[str] = Field(None, max_length=1000, description="应用描述")
    redirect_uris: list[str] = Field(..., min_length=1, max_length=20, description="回调地址白名单")
    scopes: list[str] = Field(default_factory=list, max_length=32, description="请求的 scope 集合")
    grant_types: Optional[list[str]] = Field(None, description="授权类型；默认 authorization_code + refresh_token")
    callback_url: str = Field(..., max_length=2048, description="安装完成回跳地址（带 code & state）")
    state: Optional[str] = Field(None, max_length=256, description="申请方 CSRF 随机串，原样回传")
    code_challenge: str = Field(..., max_length=128, description="PKCE S256 challenge")
    code_challenge_method: str = Field("S256", description="PKCE 方法（只支持 S256）")


class InstallRequestCreated(BaseModel):
    """发起安装申请的响应"""

    install_id: str
    status: str
    approval_url: str = Field(..., description="管理员确认页地址（前端 origin + approval_path）")
    approval_path: str = Field(..., description="确认页相对路径（供接入方按自己的前端 origin 拼接）")
    expires_at: str
    reused: bool = Field(False, description="true = 命中同 (client_id, code_challenge) 的既有申请")


class InstallRequestView(BaseModel):
    """安装申请视图（**不含** 安装码 / challenge / state）"""

    install_id: str
    status: str
    client_id: str
    name: str
    description: Optional[str] = None
    redirect_uris: list[str]
    scopes: list[str]
    grant_types: list[str]
    callback_url: str
    callback_host: str = Field("", description="回跳地址主机（确认页展示，防钓鱼核对）")
    expires_at: str
    created_at: str
    approved_at: Optional[str] = None
    consumed_at: Optional[str] = None
    recovery_count: int = 0
    request_ip: Optional[str] = None
    user_agent: Optional[str] = None


class InstallStatusView(BaseModel):
    """安装状态（verifier 鉴权；**不含任何密钥**）"""

    install_id: str
    status: str
    client_id: str
    created_at: str
    expires_at: str
    approved_at: Optional[str] = None
    consumed_at: Optional[str] = None
    recoverable: bool = Field(False, description="已消费且仍在恢复窗口内 → 可用同一 verifier 重试兑换")


class InstallDecisionView(BaseModel):
    """批准/拒绝的结果"""

    install_id: str
    status: str
    redirect_to: Optional[str] = Field(None, description="批准后的回跳 URL（含一次性安装码）")


class InstallExchangeRequest(BaseModel):
    """兑换请求（服务端到服务端）"""

    install_id: str = Field(..., max_length=64)
    code: str = Field(..., max_length=128, description="一次性安装码")
    verifier: str = Field(..., min_length=16, max_length=256, description="申请方持有的 verifier 明文")


class InstallExchangeView(BaseModel):
    """兑换结果（**client_secret 明文仅此一次**）"""

    client_id: str
    client_secret: str = Field(..., description="客户端密钥明文——仅此一次，请立即保存")
    name: str
    description: Optional[str] = None
    redirect_uris: list[str]
    scopes: list[str]
    grant_types: list[str]
    recovered: bool = Field(False, description="true = 走的是恢复路径（首次兑换响应丢失后的补偿）")


class InstallStatusRequest(BaseModel):
    """状态查询请求（verifier 走 body，不进 URL）"""

    install_id: str = Field(..., max_length=64)
    verifier: str = Field(..., min_length=16, max_length=256)
