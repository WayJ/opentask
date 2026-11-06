"""OAuth 自动接入（Install Flow）服务

协议契约（权威）：``docs/superpowers/contracts/2026-11-06-e101-oauth2-install-contract.md``
设计：``docs/superpowers/specs/2026-11-06-e101-oauth2-install-flow-design.md``

流程（PKCE 风格，**无长期凭据**）：

1. 小蓝生成一次性高熵 ``verifier``，只把 ``challenge = BASE64URL(SHA256(verifier))`` 推给 OpenTask；
2. OpenTask 建 **PENDING** 申请（只存 challenge，从不接触 verifier）；
3. 管理员登录确认 → 申请置 **APPROVED**，签发**一次性安装码**（只存哈希），并回跳
   ``callback_url?code=…&state=…``；
4. 小蓝**服务端**用 ``verifier`` 兑换 → OpenTask 校验 challenge 绑定、code、有效期、单次消费，
   **此时才创建 client** 并轮换出密钥（库里只存哈希），明文只进本次响应。

安全口径（详见契约 §5/§6）：

- **密钥零落库明文**：client_secret 只在兑换响应体出现一次；批准阶段不创建 client；
- **consumed ≠ 成功**：只有 2xx 且响应体含 ``client_secret`` 才算成功；恢复窗口内用同一
  verifier 重试可换发**新密钥**，窗口外必须重新发起安装；
- **未认证发起有上限**：全局/单 IP pending 配额 + 单 IP 速率 + 幂等复用 + 15 分钟存活期；
- **开放重定向**：``callback_url`` 严格校验（绝对 URL、https、无 userinfo/fragment/控制字符）+
  **主机绑定**（须是某个 redirect_uris 主机或其子域），且**回跳前二次校验**；
- **SSRF**：OpenTask **不对来方提供的任何 URL 发起服务端请求**，故无 SSRF 面。
"""

import base64
import hashlib
import ipaddress
import logging
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode, urlsplit

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.config import config
from opentask.models.oauth2.model import OAuthClient, OAuthInstallRequest
from opentask.services.oauth2.client_service import (
    generate_client_secret,
    hash_secret,
    split_redirect_uris,
    split_scopes,
)

logger = logging.getLogger(__name__)

# ===== 状态 =====
STATUS_PENDING = "PENDING"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_EXPIRED = "EXPIRED"
STATUS_CONSUMED = "CONSUMED"

# ===== 安装码 =====
# 安装码前缀（与 client_secret 的 ocs_、installer 概念都区分开）
INSTALL_CODE_PREFIX = "ins_"
# 安装码随机字节数
INSTALL_CODE_BYTES = 16

# ===== 校验上限 =====
MAX_REDIRECT_URIS = 20
MAX_REDIRECT_URI_LEN = 2048
MAX_SCOPES = 32
MAX_SCOPE_LEN = 64
MAX_CALLBACK_LEN = 2048
MAX_CLIENT_ID_LEN = 64
MAX_NAME_LEN = 255
MAX_DESCRIPTION_LEN = 1000
MAX_STATE_LEN = 256
MAX_GRANT_TYPES = 4

# 允许的 grant_type
ALLOWED_GRANT_TYPES = {"authorization_code", "refresh_token"}
DEFAULT_GRANT_TYPES = ["authorization_code", "refresh_token"]

# PKCE：只接受 S256（拒绝 plain 降级）
CODE_CHALLENGE_METHOD = "S256"
# BASE64URL(SHA256(verifier)) 的字符长度
CHALLENGE_LEN = 43

# 回环主机（开发环境允许 http）
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}

_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_SCOPE_RE = re.compile(r"^[A-Za-z0-9:._-]{1,64}$")
_CHALLENGE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x20\x7f]")


# ===== 异常 =====


class InstallValidationError(Exception):
    """字段校验失败（422）"""

    code = "invalid_request"


class InstallConflictError(Exception):
    """状态/唯一性冲突（409）"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class InstallNotFoundError(Exception):
    """申请不存在（404）"""

    code = "install_request_not_found"


class InstallLimitError(Exception):
    """触发滥用上限（429）"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class InstallAuthError(Exception):
    """verifier / code 校验失败（400）"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ===== 工具函数 =====


def hash_code(code: str) -> str:
    """安装码 → SHA-256 十六进制哈希"""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def s256_challenge(verifier: str) -> str:
    """PKCE S256：verifier → BASE64URL(SHA256(verifier))"""
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def verify_challenge(verifier: str, challenge: str) -> bool:
    """恒定时间校验 verifier ↔ challenge"""
    if not verifier or not challenge:
        return False
    return secrets.compare_digest(s256_challenge(verifier), challenge)


def generate_install_code() -> str:
    """生成一次性安装码明文"""
    return INSTALL_CODE_PREFIX + secrets.token_hex(INSTALL_CODE_BYTES)


def _is_loopback(host: str) -> bool:
    """是否回环主机（含 ::1 与 127.0.0.0/8）"""
    if host in LOOPBACK_HOSTS:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _parse_absolute_url(url: str, *, field: str) -> tuple[str, str, int]:
    """严格解析绝对 URL，返回 (scheme, host, port)；失败抛 InstallValidationError

    口径（开放重定向缓解 M1）：
    - 禁控制字符与空白（防 CRLF 注入与解析歧义）；
    - scheme ∈ {http, https}；
    - 必须有 netloc，且**禁 userinfo**（`https://a@b` 型混淆）；
    - **禁 fragment**；
    - 禁 IP 字面量（回环除外）；
    - 禁 netloc 中的反斜杠（浏览器与解析器差异）。
    """
    if not url or len(url) > MAX_CALLBACK_LEN:
        raise InstallValidationError(f"{field} 长度非法")
    if _CONTROL_CHARS_RE.search(url):
        raise InstallValidationError(f"{field} 含非法字符（空白/控制字符）")
    if "\\" in url:
        raise InstallValidationError(f"{field} 含非法字符")

    try:
        parsed = urlsplit(url)
    except ValueError as exc:  # pragma: no cover - urlsplit 极少抛错
        raise InstallValidationError(f"{field} 不是合法 URL：{exc}") from exc

    if parsed.scheme not in ("http", "https"):
        raise InstallValidationError(f"{field} 必须是 http(s) 绝对 URL")
    if not parsed.netloc:
        raise InstallValidationError(f"{field} 必须是绝对 URL")
    if parsed.username or parsed.password:
        raise InstallValidationError(f"{field} 不得包含用户信息（userinfo）")
    if parsed.fragment:
        raise InstallValidationError(f"{field} 不得包含 fragment")
    if "\\" in parsed.netloc:
        raise InstallValidationError(f"{field} 含非法字符")

    host = (parsed.hostname or "").lower()
    if not host:
        raise InstallValidationError(f"{field} 缺少主机名")

    # IP 字面量：仅回环允许（本地开发），其余一律拒绝
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not _is_loopback(host):
            raise InstallValidationError(f"{field} 不得使用 IP 字面量主机")

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise InstallValidationError(f"{field} 端口非法") from exc

    return parsed.scheme, host, port


def validate_redirect_uris(redirect_uris: list[str]) -> list[str]:
    """校验回调地址白名单：非空、去重、绝对 http(s) URL、规模上限"""
    if not redirect_uris:
        raise InstallValidationError("redirect_uris 不能为空")
    if len(redirect_uris) > MAX_REDIRECT_URIS:
        raise InstallValidationError(f"redirect_uris 最多 {MAX_REDIRECT_URIS} 条")

    seen: list[str] = []
    for uri in redirect_uris:
        uri = uri.strip()
        if len(uri) > MAX_REDIRECT_URI_LEN:
            raise InstallValidationError(f"redirect_uri 过长（>{MAX_REDIRECT_URI_LEN}）")
        _parse_absolute_url(uri, field="redirect_uri")
        if uri not in seen:
            seen.append(uri)
    if not seen:
        raise InstallValidationError("redirect_uris 不能为空")
    return seen


def validate_scopes(scopes: list[str]) -> list[str]:
    """校验 scope 列表：规模上限 + 形态"""
    if len(scopes) > MAX_SCOPES:
        raise InstallValidationError(f"scopes 最多 {MAX_SCOPES} 条")
    cleaned: list[str] = []
    for scope in scopes:
        scope = scope.strip()
        if not scope:
            continue
        if len(scope) > MAX_SCOPE_LEN or not _SCOPE_RE.match(scope):
            raise InstallValidationError(f"scope 形态非法：{scope}")
        if scope not in cleaned:
            cleaned.append(scope)
    return cleaned


def validate_grant_types(grant_types: Optional[list[str]]) -> list[str]:
    """校验 grant_type：只允许 authorization_code / refresh_token"""
    if not grant_types:
        return list(DEFAULT_GRANT_TYPES)
    if len(grant_types) > MAX_GRANT_TYPES:
        raise InstallValidationError("grant_types 过多")
    cleaned: list[str] = []
    for grant in grant_types:
        grant = grant.strip()
        if grant not in ALLOWED_GRANT_TYPES:
            raise InstallValidationError(f"不支持的 grant_type：{grant}")
        if grant not in cleaned:
            cleaned.append(grant)
    return cleaned or list(DEFAULT_GRANT_TYPES)


def validate_callback_url(callback_url: str, redirect_uris: list[str]) -> str:
    """校验安装回跳地址（开放重定向缓解 M1 + M2）

    - M1：绝对 URL、https（回环允许 http）、无 userinfo/fragment/控制字符、禁 IP 字面量；
    - M2：主机必须是某个 redirect_uris 主机**或其子域**。
    """
    callback_url = (callback_url or "").strip()
    if not callback_url or len(callback_url) > MAX_CALLBACK_LEN:
        raise InstallValidationError("callback_url 长度非法")

    scheme, host, port = _parse_absolute_url(callback_url, field="callback_url")
    if scheme != "https" and not _is_loopback(host):
        raise InstallValidationError("callback_url 必须使用 https（回环主机例外）")

    allowed_hosts: list[tuple[str, int]] = []
    for uri in redirect_uris:
        _, r_host, r_port = _parse_absolute_url(uri, field="redirect_uri")
        allowed_hosts.append((r_host, r_port))

    for r_host, r_port in allowed_hosts:
        if host == r_host and port == r_port:
            return callback_url
        if host.endswith(f".{r_host}") and port == r_port:
            return callback_url

    raise InstallValidationError(
        "callback_url 主机必须与某个 redirect_uri 主机相同或是其子域"
    )


def build_redirect_to(callback_url: str, code: str, state: Optional[str]) -> str:
    """拼装安装完成回跳 URL（code + state）"""
    params = {"code": code}
    if state:
        params["state"] = state
    separator = "&" if "?" in callback_url else "?"
    return f"{callback_url}{separator}{urlencode(params)}"


class OAuthInstallService:
    """OAuth 自动接入（安装流）服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ===== 发起申请 =====

    async def create_request(
        self,
        *,
        client_id: str,
        name: str,
        description: Optional[str],
        redirect_uris: list[str],
        scopes: list[str],
        grant_types: Optional[list[str]],
        callback_url: str,
        state: Optional[str],
        code_challenge: str,
        code_challenge_method: str,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[OAuthInstallRequest, bool]:
        """创建安装申请，返回 (申请, 是否复用)

        - **幂等**：同 ``client_id`` + 同 ``code_challenge`` 且仍在有效期内 → 复用既有申请；
        - **配额**：全局 pending 上限 / 单 IP pending 上限 / 单 IP 每分钟速率上限。
        """
        # ---- 字段校验 ----
        if code_challenge_method != CODE_CHALLENGE_METHOD:
            raise InstallValidationError("code_challenge_method 只支持 S256")
        if not code_challenge or not _CHALLENGE_RE.match(code_challenge):
            raise InstallValidationError("code_challenge 必须是 BASE64URL(SHA256(verifier))")

        client_id = (client_id or "").strip()
        if not client_id or len(client_id) > MAX_CLIENT_ID_LEN or not _CLIENT_ID_RE.match(client_id):
            raise InstallValidationError("client_id 形态非法（1-64 位 [A-Za-z0-9._-]）")

        name = (name or "").strip()
        if not name or len(name) > MAX_NAME_LEN:
            raise InstallValidationError(f"name 必填且不超过 {MAX_NAME_LEN} 字")
        if description and len(description) > MAX_DESCRIPTION_LEN:
            raise InstallValidationError(f"description 超过 {MAX_DESCRIPTION_LEN} 字")

        clean_redirects = validate_redirect_uris(redirect_uris)
        clean_scopes = validate_scopes(scopes)
        clean_grants = validate_grant_types(grant_types)
        clean_callback = validate_callback_url(callback_url, clean_redirects)

        if state and len(state) > MAX_STATE_LEN:
            raise InstallValidationError(f"state 超过 {MAX_STATE_LEN} 字")

        # ---- 幂等复用 ----
        now = datetime.utcnow()
        existing = await self._find_pending_by_client(client_id, code_challenge, now)
        if existing is not None:
            return existing, True

        # ---- client_id 冲突（已是正式 client）----
        if await self._client_exists(client_id):
            raise InstallConflictError(
                "client_id_conflict", f"client_id 已存在: {client_id}"
            )

        # ---- 滥用上限 ----
        await self._check_pending_quota(request_ip, now)

        record = OAuthInstallRequest(
            client_id=client_id,
            name=name,
            description=description,
            redirect_uris=",".join(clean_redirects),
            scopes=" ".join(clean_scopes),
            grant_types=" ".join(clean_grants),
            callback_url=clean_callback,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            status=STATUS_PENDING,
            expires_at=now + timedelta(seconds=config.oauth_install_request_ttl_seconds),
            request_ip=request_ip,
            user_agent=user_agent,
            created_at=now,
            updated_at=now,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        logger.info(
            "收到 OAuth 安装申请: client_id=%s（来源 IP 已记录，数量不打印）", client_id
        )
        return record, False

    async def _find_pending_by_client(
        self, client_id: str, code_challenge: str, now: datetime
    ) -> Optional[OAuthInstallRequest]:
        """同 client_id + 同 challenge 的有效 PENDING 申请（幂等复用）"""
        result = await self.session.execute(
            select(OAuthInstallRequest).where(
                OAuthInstallRequest.client_id == client_id,
                OAuthInstallRequest.code_challenge == code_challenge,
                OAuthInstallRequest.status == STATUS_PENDING,
                OAuthInstallRequest.expires_at > now,
            )
        )
        return result.scalars().first()

    async def _client_exists(self, client_id: str) -> bool:
        result = await self.session.execute(
            select(OAuthClient.id).where(OAuthClient.client_id == client_id)
        )
        return result.scalar_one_or_none() is not None

    async def _check_pending_quota(self, request_ip: Optional[str], now: datetime) -> None:
        """pending 配额与速率上限（未认证发起的滥用防线）"""
        global_cap = config.oauth_install_max_pending_global
        per_ip_cap = config.oauth_install_max_pending_per_ip
        rate_cap = config.oauth_install_rate_limit_per_minute

        total = await self._count_pending(now, None)
        if total >= global_cap:
            raise InstallLimitError(
                "too_many_pending_requests", "待处理安装申请已达上限，请稍后再试"
            )

        if request_ip:
            per_ip = await self._count_pending(now, request_ip)
            if per_ip >= per_ip_cap:
                raise InstallLimitError(
                    "too_many_pending_requests", "该来源的待处理安装申请已达上限"
                )
            recent = await self._count_created_since(now - timedelta(minutes=1), request_ip)
            if recent >= rate_cap:
                raise InstallLimitError("rate_limited", "请求过于频繁，请稍后再试")

    async def _count_pending(self, now: datetime, request_ip: Optional[str]) -> int:
        stmt = select(func.count()).select_from(OAuthInstallRequest).where(
            OAuthInstallRequest.status == STATUS_PENDING,
            OAuthInstallRequest.expires_at > now,
        )
        if request_ip:
            stmt = stmt.where(OAuthInstallRequest.request_ip == request_ip)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def _count_created_since(self, since: datetime, request_ip: Optional[str]) -> int:
        stmt = select(func.count()).select_from(OAuthInstallRequest).where(
            OAuthInstallRequest.created_at >= since,
        )
        if request_ip:
            stmt = stmt.where(OAuthInstallRequest.request_ip == request_ip)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    # ===== 查询 =====

    async def get_request(self, install_id: str) -> Optional[OAuthInstallRequest]:
        result = await self.session.execute(
            select(OAuthInstallRequest).where(OAuthInstallRequest.id == install_id)
        )
        return result.scalars().first()

    async def get_by_id_or_404(self, install_id: str) -> OAuthInstallRequest:
        record = await self.get_request(install_id)
        if record is None:
            raise InstallNotFoundError("安装申请不存在")
        return record

    async def list_requests(self, limit: int = 50) -> list[OAuthInstallRequest]:
        """审计列表：最近 N 条（不含 code/challenge/state 等敏感字段）"""
        result = await self.session.execute(
            select(OAuthInstallRequest)
            .order_by(OAuthInstallRequest.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    def verifier_matches(self, record: OAuthInstallRequest, verifier: str) -> bool:
        """verifier ↔ challenge 绑定校验（恒定时间）"""
        return verify_challenge(verifier, record.code_challenge)

    # ===== 批准 / 拒绝 =====

    async def approve(
        self, install_id: str, approved_by: str
    ) -> tuple[OAuthInstallRequest, str, str]:
        """管理员批准安装，返回 (申请, 安装码明文, 回跳 URL)

        - 幂等保护：仅 ``PENDING`` 可批准（条件更新，影响 0 行 → 409）；
        - **批准阶段不创建 client**：client 在兑换时才创建（密钥零落库明文，且未兑换即无残留 client）；
        - 批准时**复核**回调白名单/scopes/callback_url（防存储期篡改）；
        - 回跳前**二次校验** callback_url（开放重定向缓解 M1/M2）。
        """
        record = await self.get_by_id_or_404(install_id)
        now = datetime.utcnow()

        if record.status != STATUS_PENDING:
            raise InstallConflictError(
                "install_request_not_pending", f"申请当前状态为 {record.status}，不可重复批准"
            )
        if record.expires_at <= now:
            record.status = STATUS_EXPIRED
            record.updated_at = now
            await self.session.commit()
            raise InstallConflictError("install_request_not_pending", "申请已过期")

        # 复核内容（存储期可能被篡改）
        redirect_uris = split_redirect_uris(record.redirect_uris)
        validate_redirect_uris(redirect_uris)
        validate_scopes(sorted(split_scopes(record.scopes)))
        validate_callback_url(record.callback_url, redirect_uris)

        if await self._client_exists(record.client_id):
            raise InstallConflictError(
                "client_id_conflict", f"client_id 已存在: {record.client_id}"
            )

        code_plain = generate_install_code()
        code_expires_at = now + timedelta(seconds=config.oauth_install_code_ttl_seconds)

        # 条件更新：只有 PENDING 能被批准（并发下第二个请求影响 0 行）
        result = await self.session.execute(
            update(OAuthInstallRequest)
            .where(
                OAuthInstallRequest.id == record.id,
                OAuthInstallRequest.status == STATUS_PENDING,
            )
            .values(
                status=STATUS_APPROVED,
                code_hash=hash_code(code_plain),
                code_expires_at=code_expires_at,
                approved_by=approved_by,
                approved_at=now,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            await self.session.rollback()
            raise InstallConflictError("install_request_not_pending", "申请已被处理")

        await self.session.commit()
        await self.session.refresh(record)

        # 回跳前二次校验 callback_url（M1/M2）
        redirect_to = build_redirect_to(
            validate_callback_url(record.callback_url, redirect_uris),
            code_plain,
            record.state,
        )
        logger.info("已批准 OAuth 安装申请: client_id=%s", record.client_id)
        return record, code_plain, redirect_to

    async def reject(self, install_id: str, rejected_by: str) -> OAuthInstallRequest:
        """管理员拒绝安装"""
        record = await self.get_by_id_or_404(install_id)
        now = datetime.utcnow()
        if record.status != STATUS_PENDING:
            raise InstallConflictError(
                "install_request_not_pending", f"申请当前状态为 {record.status}，不可拒绝"
            )
        result = await self.session.execute(
            update(OAuthInstallRequest)
            .where(
                OAuthInstallRequest.id == record.id,
                OAuthInstallRequest.status == STATUS_PENDING,
            )
            .values(
                status=STATUS_REJECTED,
                rejected_at=now,
                approved_by=rejected_by,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            await self.session.rollback()
            raise InstallConflictError("install_request_not_pending", "申请已被处理")
        await self.session.commit()
        await self.session.refresh(record)
        logger.info("已拒绝 OAuth 安装申请: client_id=%s", record.client_id)
        return record

    # ===== 兑换 =====

    async def exchange(
        self, install_id: str, code: str, verifier: str
    ) -> dict:
        """服务端兑换：返回 client_id + client_secret（明文仅此一次）

        语义（契约 §3.F / §4）：
        - verifier ↔ challenge 绑定校验失败 → 400 ``invalid_verifier``；
        - 首次兑换：消费安装码（条件更新，单次）+ **创建 client** + 返回明文密钥；
        - **恢复路径**：已 CONSUMED 且在恢复窗口内 → 轮换出新密钥返回（响应丢失时的补偿）；
        - 窗口外 → 409 ``install_already_consumed``（**失败**，小蓝必须重新发起安装）。
        """
        record = await self.get_by_id_or_404(install_id)
        now = datetime.utcnow()

        # 1) verifier ↔ challenge 绑定
        if not self.verifier_matches(record, verifier):
            raise InstallAuthError("invalid_verifier", "verifier 与申请不匹配")

        # 2) 已消费 → 走恢复路径或明确失败
        if record.status == STATUS_CONSUMED:
            return await self._recover_exchange(record, now)

        if record.status != STATUS_APPROVED:
            raise InstallConflictError(
                "install_not_approved", f"申请当前状态为 {record.status}，尚未批准"
            )

        # 3) 安装码有效期
        if record.code_expires_at is None or record.code_expires_at <= now:
            raise InstallAuthError("install_code_expired", "安装码已过期")

        # 4) 安装码比对
        if not record.code_hash or not secrets.compare_digest(record.code_hash, hash_code(code)):
            raise InstallAuthError("invalid_install_code", "安装码无效")

        # 5) 原子消费（单次）+ 创建 client（同事务）
        client_secret = generate_client_secret()
        await self._create_client_for_install(record, client_secret)

        result = await self.session.execute(
            update(OAuthInstallRequest)
            .where(
                OAuthInstallRequest.id == record.id,
                OAuthInstallRequest.status == STATUS_APPROVED,
                OAuthInstallRequest.consumed_at.is_(None),
            )
            .values(
                status=STATUS_CONSUMED,
                consumed_at=now,
                first_exchange_at=now,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            await self.session.rollback()
            raise InstallConflictError("install_already_consumed", "安装码已被兑换")
        await self.session.commit()
        await self.session.refresh(record)

        logger.info("OAuth 安装兑换成功: client_id=%s", record.client_id)
        return self._credentials(record, client_secret, recovered=False)

    async def _create_client_for_install(
        self, record: OAuthInstallRequest, client_secret: str
    ) -> None:
        """按批准内容创建 client（**不单独提交**，与消费安装码同一事务）"""
        if not record.approved_by:
            raise InstallConflictError("install_not_approved", "申请缺少批准人，无法创建客户端")
        now = datetime.utcnow()
        client = OAuthClient(
            client_id=record.client_id,
            client_secret_hash=hash_secret(client_secret),
            client_secret_prefix=client_secret[:8],
            name=record.name,
            description=record.description,
            redirect_uris=record.redirect_uris,
            scopes=record.scopes,
            grant_types=record.grant_types,
            status="ACTIVE",
            created_by=record.approved_by,
            created_at=now,
            updated_at=now,
        )
        self.session.add(client)
        try:
            await self.session.flush()
        except IntegrityError as exc:  # client_id 唯一索引冲突
            await self.session.rollback()
            raise InstallConflictError(
                "client_id_conflict", f"client_id 已存在: {record.client_id}"
            ) from exc

    async def _recover_exchange(
        self, record: OAuthInstallRequest, now: datetime
    ) -> dict:
        """恢复路径：首次兑换响应丢失时，用同一 verifier 换发**新密钥**

        - 窗口内 → 轮换密钥并返回（``recovered=True``）；
        - 窗口外 → 409 ``install_already_consumed``（**明确失败**，必须重新发起安装）。
        """
        anchor = record.first_exchange_at or record.consumed_at
        if anchor is None:
            raise InstallConflictError("install_already_consumed", "安装码已被兑换")
        window_end = anchor + timedelta(seconds=config.oauth_install_recovery_window_seconds)
        if now > window_end:
            raise InstallConflictError(
                "install_already_consumed",
                "安装码已被兑换且恢复窗口已过，请重新发起安装",
            )

        client = await self._get_client(record.client_id)
        if client is None:
            raise InstallConflictError("install_already_consumed", "客户端不存在，无法恢复")

        new_secret = generate_client_secret()
        client.client_secret_hash = hash_secret(new_secret)
        client.client_secret_prefix = new_secret[:8]
        client.updated_at = now
        record.recovery_count = (record.recovery_count or 0) + 1
        record.recovery_used_at = now
        record.updated_at = now
        await self.session.commit()

        logger.info(
            "OAuth 安装兑换恢复: client_id=%s（第 %s 次恢复）",
            record.client_id,
            record.recovery_count,
        )
        return self._credentials(record, new_secret, recovered=True)

    async def _get_client(self, client_id: str) -> Optional[OAuthClient]:
        result = await self.session.execute(
            select(OAuthClient).where(OAuthClient.client_id == client_id)
        )
        return result.scalars().first()

    def _credentials(self, record: OAuthInstallRequest, secret: str, *, recovered: bool) -> dict:
        """兑换响应体（**明文密钥仅此一次**）"""
        return {
            "client_id": record.client_id,
            "client_secret": secret,
            "name": record.name,
            "description": record.description,
            "redirect_uris": split_redirect_uris(record.redirect_uris),
            "scopes": sorted(split_scopes(record.scopes)),
            "grant_types": sorted(split_scopes(record.grant_types)),
            "recovered": recovered,
        }
