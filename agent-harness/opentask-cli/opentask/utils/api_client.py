"""OpenTask API Client - HTTP client for backend API communication."""
import json
import logging
from typing import Any
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# Enum Value Conversion Utilities
# ============================================================================

def _normalize_priority(priority: str | None) -> str | None:
    """Normalize priority value to API format (lowercase).

    Args:
        priority: Priority value (e.g., "low", "medium", "high", "LOW", "MEDIUM", "HIGH")

    Returns:
        Lowercase priority value (e.g., "low", "medium", "high", "critical")
    """
    if not priority:
        return None
    return priority.lower()


def _normalize_requirement_status(status: str | None) -> str | None:
    """Convert CLI requirement status to API format (lowercase).

    Maps simple CLI status values to API requirement statuses:
    - draft -> draft
    - active -> clarifying
    - completed -> released
    - archived -> archived

    Args:
        status: Status value from CLI

    Returns:
        API-compatible status value (lowercase)
    """
    if not status:
        return None

    status_map = {
        "planning": "planning",
        "generating": "generating",
        "evaluating": "evaluating",
        "completed": "completed",
        "closed": "closed",
        "archived": "archived",
        # 兼容旧状态值
        "draft": "planning",
        "clarifying": "planning",
        "spec_ready": "planning",
        "designing": "planning",
        "coding": "generating",
        "reviewing": "evaluating",
        "testing": "evaluating",
        "released": "completed",
    }

    # Map lowercase CLI values to API values (lowercase)
    return status_map.get(status.lower(), status.lower())


def _format_error_details(response_data: dict) -> str:
    """Format detailed error information from API response.

    Args:
        response_data: Response data from API

    Returns:
        Formatted error message with details
    """
    if not response_data:
        return ""

    details = []

    # Check for validation errors
    if "detail" in response_data:
        detail = response_data["detail"]
        if isinstance(detail, list):
            # FastAPI validation errors
            for err in detail:
                loc = " -> ".join(str(l) for l in err.get("loc", []))
                msg = err.get("msg", "")
                details.append(f"  - {loc}: {msg}")
        elif isinstance(detail, dict):
            details.append(f"  {detail}")
        else:
            details.append(f"  {detail}")

    # Check for standard error message
    if "message" in response_data:
        details.append(f"  Message: {response_data['message']}")

    return "\n".join(details) if details else ""


class APIError(Exception):
    """API error with status code and message."""

    def __init__(self, message: str, status_code: int = 0, response_data: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON output.

        Returns:
            Dictionary with error details
        """
        return {
            "success": False,
            "error": f"HTTP {self.status_code}" if self.status_code else "API Error",
            "message": self.message,
            "status_code": self.status_code,
            "details": self.response_data
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert error to JSON string.

        Args:
            indent: JSON indentation (default: 2)

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def _get_diagnostic_suggestions(error: APIError, command_context: str | None = None) -> list[str]:
    """Get diagnostic suggestions for common errors.

    Args:
        error: The API error that occurred
        command_context: Context about which command was running

    Returns:
        List of diagnostic suggestions
    """
    suggestions = []

    # HTTP 422 - Validation errors
    if error.status_code == 422:
        if "title" in str(error.response_data):
            suggestions.append("- Missing required field: title")
            suggestions.append("  Fix: Add -t, --title parameter")

        if "priority" in str(error.response_data):
            suggestions.append("- Invalid priority value")
            suggestions.append("  Fix: Use one of: low, medium, high, critical")

        if "status" in str(error.response_data):
            suggestions.append("- Invalid status value")
            if command_context == "requirement":
                suggestions.append("  Fix: Use one of: draft, active, completed, archived")
            else:
                suggestions.append("  Fix: Use one of: open, in_progress, resolved, closed")

        if "project_id" in str(error.response_data):
            suggestions.append("- Missing or invalid project_id")
            suggestions.append("  Fix: Set active project with 'opentask project use <ID>'")
            suggestions.append("  Fix: Or add --project <ID> parameter")

    # HTTP 401/403 - Authentication errors
    if error.status_code in (401, 403):
        suggestions.append("- Authentication failed")
        suggestions.append("  Fix: Run 'opentask config login' to re-authenticate")
        suggestions.append("  Fix: Or set new token with 'opentask config set-token <TOKEN>'")

    # HTTP 404 - Not found
    if error.status_code == 404:
        suggestions.append("- Resource not found")
        suggestions.append("  Fix: Check the ID is correct")
        suggestions.append("  Fix: Verify you have access to this resource")

    # Connection errors
    if "Connection refused" in error.message or "timeout" in error.message.lower():
        suggestions.append("- Cannot connect to API server")
        suggestions.append("  Fix: Check if backend is running")
        suggestions.append("  Fix: Verify API URL with 'opentask config show'")

    return suggestions


class OpenTaskClient:
    """HTTP client for OpenTask backend API.

    Handles authentication, request/response formatting, and error handling.
    """

    def __init__(self, base_url: str = "http://localhost:7377", token: str | None = None, config: "Config | None" = None):
        """Initialize API client.

        Args:
            base_url: Base URL of the backend API
            token: JWT authentication token (optional)
            config: Config object for auto-relogin (optional)
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.config = config
        self.timeout = 30.0
        self._relogin_attempts = 0  # Track relogin attempts to prevent infinite loops
        self._max_relogin_attempts = 1  # Allow only one relogin attempt per request

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication and workspace context.

        Access Token takes priority over JWT token.
        When config has active_workspace_id, send X-Workspace-Id (FE-aligned).
        """
        headers = {
            "Content-Type": "application/json",
        }
        # Access Token 优先于 JWT token
        effective_token = None
        if self.config and self.config.access_token:
            effective_token = self.config.access_token
        elif self.token:
            effective_token = self.token

        if effective_token:
            headers["Authorization"] = f"Bearer {effective_token}"

        # Workspace context (required by cycles/tags/triage/…)
        if self.config and getattr(self.config, "active_workspace_id", None):
            headers["X-Workspace-Id"] = self.config.active_workspace_id
        return headers

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and extract data.

        Supports multiple API response formats:
        - Standard: {"code": 200, "data": {...}}
        - FastAPI errors: {"detail": [...]}
        - Simple errors: {"message": "..."}

        Args:
            response: HTTP response object

        Returns:
            Response data dictionary

        Raises:
            APIError: If request failed
        """
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {}

        # Extract error message from various formats
        error_msg = None
        status_code = None

        # Format 1: Standard wrapper {"code": ..., "data": ..., "message": ...}
        if "code" in data:
            status_code = data["code"]
            if status_code != 200:
                # Try multiple fields for error message
                error_msg = (
                    data.get("message") or
                    data.get("error") or
                    data.get("msg") or
                    f"HTTP {status_code}"
                )
                # Add detail if present (FastAPI validation errors)
                if "detail" in data:
                    detail = data["detail"]
                    if isinstance(detail, list):
                        # FastAPI validation error format
                        detail_msgs = []
                        for err in detail:
                            loc = " -> ".join(str(l) for l in err.get("loc", []))
                            msg = err.get("msg", "")
                            if loc and msg:
                                detail_msgs.append(f"{loc}: {msg}")
                        if detail_msgs:
                            error_msg = f"{error_msg}\n" + "\n".join(detail_msgs)
                    elif isinstance(detail, str):
                        error_msg = f"{error_msg}\n{detail}"
                raise APIError(
                    message=error_msg,
                    status_code=status_code,
                    response_data=data
                )
            return data.get("data", data)

        # Format 2: FastAPI error format {"detail": [...]}
        if "detail" in data:
            detail = data["detail"]
            if isinstance(detail, list):
                # Validation errors - check if it's an error
                if response.status_code >= 400 or any("msg" in item for item in detail):
                    detail_msgs = []
                    for err in detail:
                        loc = " -> ".join(str(l) for l in err.get("loc", []))
                        msg = err.get("msg", "")
                        type_ = err.get("type", "")
                        if loc and msg:
                            detail_msgs.append(f"{loc}: {msg}")
                    error_msg = "Validation error:\n" + "\n".join(detail_msgs)
                    raise APIError(
                        message=error_msg,
                        status_code=response.status_code or 422,
                        response_data=data
                    )
            elif isinstance(detail, str) and response.status_code >= 400:
                error_msg = detail
                raise APIError(
                    message=error_msg,
                    status_code=response.status_code,
                    response_data=data
                )

        # Format 3: Simple error {"message": "...", "error": "..."}
        if response.status_code >= 400:
            error_msg = (
                data.get("message") or
                data.get("error") or
                data.get("msg") or
                f"HTTP {response.status_code}"
            )
            raise APIError(
                message=error_msg,
                status_code=response.status_code,
                response_data=data
            )

        # Format 4: Successful response without code wrapper
        return data

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> dict[str, Any]:
        """Make async HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx

        Returns:
            Response data dictionary

        Raises:
            APIError: If request failed
        """
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._get_headers(),
                    **kwargs
                )
                return self._handle_response(response)

        except httpx.TimeoutException:
            # Reset counter on timeout
            self._relogin_attempts = 0
            raise APIError(f"Request timeout: {url}")
        except httpx.ConnectError:
            # Reset counter on connection error
            self._relogin_attempts = 0
            raise APIError(f"Connection refused: {url}")
        except APIError as e:
            # Access Token 失效时自动清理
            if e.status_code in (401, 403) and self.config and self.config.access_token:
                logger.warning("Access Token 失效，已自动清理")
                self.config.delete("access_token")

            # 401 处理链: refresh_token 刷新 → 凭据重登 → 清空凭据
            # 防止无限循环:只允许一次刷新/重登尝试
            if (e.status_code in (401, 403) and
                self.config and
                self._relogin_attempts < self._max_relogin_attempts):
                return await self._handle_relogin(e, method, url, kwargs)

            # Reset counter before raising the error
            self._relogin_attempts = 0
            raise
        except Exception as e:
            # Reset counter on other exceptions
            self._relogin_attempts = 0
            raise APIError(f"Request failed: {str(e)}")

    def _clear_saved_credentials(self):
        """清空保存的登录凭据（keyring + config）。

        用于重登失败时（凭据已过期，或为迁移前保存的 SSO 加密密文，
        二者无法区分），避免后续请求继续用过期凭据重试。
        """
        if not self.config:
            return

        username = self.config.username
        self.config.delete("a_u")
        self.config.delete("a_p")
        # refresh_token 已确认失效，一并清理
        self.config.delete("refresh_token")

        # 同步清理 keyring 中的凭据
        if username:
            try:
                from .password_store import PasswordStore
                if PasswordStore.is_available():
                    PasswordStore.delete_password(username)
            except Exception as e:
                logger.warning(f"Failed to delete credentials from keyring: {e}")

        logger.info("已清空保存的登录凭据，请重新执行 opentask login")

    async def _handle_relogin(
        self,
        original_error: APIError,
        method: str,
        url: str,
        kwargs: dict
    ) -> dict[str, Any]:
        """401/403 处理链：refresh_token 刷新 → 凭据重登 → 清空凭据。

        1. 先尝试使用 config 中保存的 refresh_token 刷新 token；
        2. 刷新失败（refresh_token 过期/不存在）则用保存的凭据明文重登一次；
        3. 重登也失败（凭据过期，或为迁移前保存的 SSO 加密密文）则清空
           keyring/config 凭据并抛出明确错误，不无限重试。

        Args:
            original_error: 原请求抛出的 401/403 APIError
            method: 原请求的 HTTP 方法
            url: 原请求的完整 URL
            kwargs: 原请求的 httpx 参数

        Returns:
            刷新/重登成功后重试原请求的响应数据

        Raises:
            APIError: 刷新与重登均失败，或重试原请求失败
        """
        # Increment relogin attempt counter（内部 login 的 401 不会再次触发本方法）
        self._relogin_attempts += 1

        try:
            # 1) 先尝试使用 refresh_token 刷新
            refreshed = await self.refresh()

            if not refreshed:
                # 2) 刷新失败，使用保存的凭据重新登录（明文密码）
                if not (self.config.username and self.config.password):
                    raise APIError(
                        "登录已过期且未保存登录凭据，请重新执行 opentask login",
                        status_code=original_error.status_code
                    )

                try:
                    login_result = await self.login(
                        self.config.username,
                        self.config.password,
                        _save_to_config=False  # Don't save again
                    )

                    new_token = login_result.get("token") or login_result.get("access_token")
                    if not new_token:
                        raise APIError("Relogin response did not contain token")
                    self.token = new_token
                    self.config.token = new_token
                    new_refresh_token = login_result.get("refreshToken") or login_result.get("refresh_token")
                    if new_refresh_token:
                        self.config.refresh_token = new_refresh_token
                except APIError:
                    # 3) 重登失败：凭据已过期，或为迁移前保存的 SSO 加密密文（无法区分）
                    #    一律清空 keyring/config 凭据，要求用户重新登录
                    self._clear_saved_credentials()
                    raise APIError(
                        "凭据已过期，请重新执行 opentask login",
                        status_code=original_error.status_code
                    ) from original_error

            # Retry the original request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._get_headers(),
                    **kwargs
                )
                # Reset counter on successful retry
                self._relogin_attempts = 0
                return self._handle_response(response)

        except APIError:
            self._relogin_attempts = 0
            raise
        except Exception as relogin_error:
            # Reset counter and raise a clear error
            self._relogin_attempts = 0
            raise APIError(
                f"Auto-relogin failed after 401/403: {str(relogin_error)}",
                status_code=original_error.status_code
            ) from relogin_error

    async def get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make GET request."""
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data: dict | None = None, params: dict | None = None) -> dict[str, Any]:
        """Make POST request."""
        kwargs: dict[str, Any] = {"json": data}
        if params is not None:
            kwargs["params"] = params
        return await self._request("POST", endpoint, **kwargs)

    async def put(self, endpoint: str, data: dict | None = None) -> dict[str, Any]:
        """Make PUT request."""
        return await self._request("PUT", endpoint, json=data)

    async def delete(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make DELETE request."""
        if params is not None:
            return await self._request("DELETE", endpoint, params=params)
        return await self._request("DELETE", endpoint)

    async def patch(self, endpoint: str, data: dict | None = None, params: dict | None = None) -> dict[str, Any]:
        """Make PATCH request."""
        kwargs: dict[str, Any] = {"json": data}
        if params is not None:
            kwargs["params"] = params
        return await self._request("PATCH", endpoint, **kwargs)

    # ============================================================================
    # Workspace API (E14)
    # ============================================================================

    async def list_workspaces(self) -> list:
        """List workspaces for current user."""
        data = await self.get("/api/workspaces")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("rows") or data.get("data") or []
        return []

    async def get_workspace(self, workspace_id: str) -> dict:
        """Get workspace details."""
        return await self.get(f"/api/workspaces/{workspace_id}")

    async def update_workspace(self, workspace_id: str, **kwargs) -> dict:
        """PATCH workspace (E50: timezone / businessHours)."""
        return await self.patch(f"/api/workspaces/{workspace_id}", data=kwargs)

    async def list_workspace_members(self, workspace_id: str) -> list:
        data = await self.get(f"/api/workspaces/{workspace_id}/members")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("rows") or data.get("data") or []
        return []

    async def add_workspace_member(self, workspace_id: str, user_id: str, role: str = "member") -> dict:
        return await self.post(
            f"/api/workspaces/{workspace_id}/members",
            data={"userId": user_id, "role": role},
        )

    async def remove_workspace_member(self, workspace_id: str, user_id: str) -> dict:
        return await self.delete(f"/api/workspaces/{workspace_id}/members/{user_id}")

    async def update_workspace_member_role(self, workspace_id: str, user_id: str, role: str) -> dict:
        return await self.patch(
            f"/api/workspaces/{workspace_id}/members/{user_id}",
            data={"role": role},
        )

    async def list_workspace_invites(self, workspace_id: str) -> list:
        data = await self.get(f"/api/workspaces/{workspace_id}/invites")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("rows") or data.get("data") or []
        return []

    async def create_workspace_invite(self, workspace_id: str, email: str | None = None, role: str = "member") -> dict:
        body: dict = {"role": role}
        if email:
            body["email"] = email
        return await self.post(f"/api/workspaces/{workspace_id}/invites", data=body)

    async def revoke_workspace_invite(self, workspace_id: str, invite_id: str) -> dict:
        return await self.delete(f"/api/workspaces/{workspace_id}/invites/{invite_id}")

    async def preview_invite(self, token: str) -> dict:
        return await self.get(f"/api/invites/{token}")

    async def accept_invite(self, token: str) -> dict:
        return await self.post(f"/api/invites/{token}/accept")

    # ============================================================================
    # Cycles API
    # ============================================================================

    async def list_cycles(self, status: str | None = None) -> dict:
        params = {}
        if status:
            params["status"] = status
        return await self.get("/api/cycles", params=params or None)

    async def get_cycle(self, cycle_id: str) -> dict:
        return await self.get(f"/api/cycles/{cycle_id}")

    async def get_cycle_capacity_hint(self, cycle_id: str | None = None) -> dict:
        """E17: cycle capacity / velocity hint (points-first)."""
        params = {}
        if cycle_id:
            params["cycle_id"] = cycle_id
        return await self.get("/api/cycles/capacity-hint", params=params or None)

    async def create_cycle(self, starts_at: str, ends_at: str, name: str | None = None) -> dict:
        data = {"starts_at": starts_at, "ends_at": ends_at}
        if name:
            data["name"] = name
        return await self.post("/api/cycles", data=data)

    async def activate_cycle(self, cycle_id: str) -> dict:
        return await self.post(f"/api/cycles/{cycle_id}/activate")

    async def complete_cycle(self, cycle_id: str) -> dict:
        return await self.post(f"/api/cycles/{cycle_id}/complete")

    async def generate_upcoming_cycle(self) -> dict:
        """E84: POST /api/cycles/generate-upcoming."""
        return await self.post("/api/cycles/generate-upcoming")

    async def update_cycle(self, cycle_id: str, **kwargs) -> dict:
        """E84: PATCH /api/cycles/{id} — only send explicit fields."""
        return await self.patch(f"/api/cycles/{cycle_id}", data=kwargs)

    async def delete_cycle(self, cycle_id: str) -> dict:
        """E84: DELETE /api/cycles/{id}."""
        return await self.delete(f"/api/cycles/{cycle_id}")

    # ============================================================================
    # Tags / Labels API
    # ============================================================================

    async def list_tags(self, group_id: str | None = None, q: str | None = None) -> dict:
        params = {}
        if group_id:
            params["group_id"] = group_id
        if q:
            params["q"] = q
        return await self.get("/api/tags", params=params or None)

    async def create_tag(self, name: str, color: str | None = None, group_id: str | None = None) -> dict:
        data: dict = {"name": name}
        if color:
            data["color"] = color
        if group_id:
            data["group_id"] = group_id
        return await self.post("/api/tags", data=data)

    async def delete_tag(self, tag_id: str | int) -> dict:
        return await self.delete(f"/api/tags/{tag_id}")

    async def attach_issue_tag(self, issue_id: str, tag_id: str | int) -> dict:
        return await self.post(f"/api/issues/{issue_id}/tags/{tag_id}")

    async def detach_issue_tag(self, issue_id: str, tag_id: str | int) -> dict:
        return await self.delete(f"/api/issues/{issue_id}/tags/{tag_id}")

    async def list_issue_tags(self, issue_id: str) -> dict:
        return await self.get(f"/api/issues/{issue_id}/tags")

    async def replace_issue_tags(self, issue_id: str, tag_ids: list[int]) -> dict:
        """E86: PUT /api/issues/{id}/tags — whole-set replace."""
        return await self.put(f"/api/issues/{issue_id}/tags", data={"tag_ids": tag_ids})

    async def update_tag(
        self,
        tag_id: str | int,
        *,
        name: str | None = None,
        color: str | None = None,
        group_id: str | None = None,
        clear_group: bool = False,
    ) -> dict:
        """E86/E87: PATCH /api/tags/{id}; group_id is UUID str."""
        body: dict = {}
        if name is not None:
            body["name"] = name
        if color is not None:
            body["color"] = color
        if group_id is not None:
            body["group_id"] = group_id
        if clear_group:
            body["clear_group"] = True
        return await self.patch(f"/api/tags/{tag_id}", data=body)


    async def list_tag_groups(self) -> dict:
        """E87: GET /api/tag-groups."""
        return await self.get("/api/tag-groups")

    async def create_tag_group(
        self, name: str, color: str | None = None, position: int = 0
    ) -> dict:
        """E87: POST /api/tag-groups."""
        data: dict = {"name": name, "position": position}
        if color is not None:
            data["color"] = color
        return await self.post("/api/tag-groups", data=data)

    async def update_tag_group(
        self,
        group_id: str,
        *,
        name: str | None = None,
        color: str | None = None,
        position: int | None = None,
    ) -> dict:
        """E87: PATCH /api/tag-groups/{id}."""
        body: dict = {}
        if name is not None:
            body["name"] = name
        if color is not None:
            body["color"] = color
        if position is not None:
            body["position"] = position
        return await self.patch(f"/api/tag-groups/{group_id}", data=body)

    async def delete_tag_group(self, group_id: str) -> dict:
        """E87: DELETE /api/tag-groups/{id}."""
        return await self.delete(f"/api/tag-groups/{group_id}")

    # ============================================================================
    # Triage API
    # ============================================================================

    async def list_triage(self, page: int = 1, page_size: int = 50) -> dict:
        return await self.get("/api/triage", params={"page": page, "page_size": page_size})

    async def enqueue_triage(self, issue_id: str | None = None, title: str | None = None, **kwargs) -> dict:
        data = dict(kwargs)
        if issue_id:
            data["issueId"] = issue_id
        if title:
            data["title"] = title
        return await self.post("/api/triage", data=data)

    async def accept_triage(self, issue_id: str) -> dict:
        return await self.post(f"/api/triage/{issue_id}/accept")

    async def decline_triage(self, issue_id: str) -> dict:
        return await self.post(f"/api/triage/{issue_id}/decline")

    async def duplicate_triage(self, issue_id: str, duplicate_of_issue_id: str) -> dict:
        return await self.post(
            f"/api/triage/{issue_id}/duplicate",
            data={"duplicateOfIssueId": duplicate_of_issue_id},
        )

    # ============================================================================
    # Inbox API
    # ============================================================================

    async def list_inbox(
        self,
        unread_only: bool = False,
        include_snoozed: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        return await self.get(
            "/api/inbox",
            params={
                "unread_only": unread_only,
                "include_snoozed": include_snoozed,
                "page": page,
                "page_size": page_size,
            },
        )

    async def inbox_read(self, notification_id: str) -> dict:
        return await self.post(f"/api/inbox/{notification_id}/read")

    async def inbox_read_all(self) -> dict:
        return await self.post("/api/inbox/read-all")

    async def inbox_snooze(self, notification_id: str, until: str) -> dict:
        return await self.post(f"/api/inbox/{notification_id}/snooze", data={"until": until})

    async def inbox_unsnooze(self, notification_id: str) -> dict:
        return await self.post(f"/api/inbox/{notification_id}/unsnooze")

    # ============================================================================
    # Favorites API
    # ============================================================================

    async def list_favorites(self) -> dict:
        return await self.get("/api/favorites")

    async def add_favorite(self, target_type: str, target_id: str) -> dict:
        return await self.post(
            "/api/favorites",
            data={"target_type": target_type, "target_id": target_id},
        )

    async def remove_favorite(self, favorite_id: str) -> dict:
        return await self.delete(f"/api/favorites/{favorite_id}")

    async def reorder_favorites(self, ordered_ids: list[str]) -> dict:
        """E88: PUT /api/favorites/reorder — ordered_ids must cover all current favorites."""
        return await self.put(
            "/api/favorites/reorder",
            data={"ordered_ids": list(ordered_ids)},
        )

    # ============================================================================
    # Issue Watchers API (E18)
    # ============================================================================

    async def list_issue_watchers(self, issue_id: str) -> list:
        data = await self.get(f"/api/issues/{issue_id}/watchers")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        return data or []

    async def watch_issue(self, issue_id: str) -> dict:
        return await self.post(f"/api/issues/{issue_id}/watchers")

    async def unwatch_issue(self, issue_id: str) -> dict:
        return await self.delete(f"/api/issues/{issue_id}/watchers")

    # ============================================================================
    # Project Watchers API (E83)
    # ============================================================================

    async def list_project_watchers(self, project_id: str) -> list:
        data = await self.get(f"/api/projects/{project_id}/watchers")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        return data or []

    async def watch_project(self, project_id: str) -> dict:
        return await self.post(f"/api/projects/{project_id}/watchers")

    async def unwatch_project(self, project_id: str) -> dict:
        return await self.delete(f"/api/projects/{project_id}/watchers")

    # ============================================================================
    # Project Health / Timeline API (E85)
    # ============================================================================

    async def get_project_health(self, project_id: str, *, history: bool = False) -> dict:
        """E85: GET project health (optional history)."""
        params = {"history": "true" if history else "false"}
        return await self.get(f"/api/projects/{project_id}/health", params=params)

    async def post_project_health(
        self, project_id: str, *, status: str, note: str | None = None
    ) -> dict:
        """E85: POST project health update."""
        body: dict = {"status": status}
        if note is not None:
            body["note"] = note
        return await self.post(f"/api/projects/{project_id}/health", data=body)

    async def get_project_timeline(self, project_id: str) -> dict:
        """E85: GET project timeline."""
        return await self.get(f"/api/projects/{project_id}/timeline")

    # ========================================================================
    # Display Prefs API (E93)
    # ========================================================================

    async def get_issue_display_prefs(self) -> dict:
        """E93: GET /api/display-prefs/issue → {display: null|object}."""
        return await self.get("/api/display-prefs/issue")

    async def put_issue_display_prefs(self, display: dict) -> dict:
        """E93: PUT /api/display-prefs/issue body {display}; keep snake_case keys."""
        return await self.put("/api/display-prefs/issue", data={"display": display})


    # ============================================================================
    # Saved Views API
    # ============================================================================

    async def list_saved_views(self) -> dict:
        return await self.get("/api/saved-views")

    async def get_saved_view(self, view_id: str) -> dict:
        return await self.get(f"/api/saved-views/{view_id}")

    async def create_saved_view(
        self,
        name: str,
        filter: dict | None = None,
        sort: dict | None = None,
        display: dict | None = None,
        is_favorite: bool | None = None,
        is_shared: bool | None = None,
    ) -> dict:
        """E92: POST /api/saved-views — snake_case body (is_favorite/is_shared/filter)."""
        body: dict = {"name": name, "filter": filter if filter is not None else {}}
        if sort is not None:
            body["sort"] = sort
        if display is not None:
            body["display"] = display
        if is_favorite is not None:
            body["is_favorite"] = bool(is_favorite)
        if is_shared is not None:
            body["is_shared"] = bool(is_shared)
        return await self.post("/api/saved-views", data=body)

    async def update_saved_view(self, view_id: str, **kwargs) -> dict:
        """E92: PATCH /api/saved-views/{id} — snake_case optional fields."""
        allowed = {"name", "filter", "sort", "display", "is_favorite", "is_shared"}
        body = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        return await self.patch(f"/api/saved-views/{view_id}", data=body)

    async def delete_saved_view(self, view_id: str) -> dict:
        """E92: DELETE /api/saved-views/{id}."""
        return await self.delete(f"/api/saved-views/{view_id}")

    async def set_saved_view_favorite(self, view_id: str, is_favorite: bool) -> dict:
        """E92: POST /api/saved-views/{id}/favorite body {is_favorite}."""
        return await self.post(
            f"/api/saved-views/{view_id}/favorite",
            data={"is_favorite": bool(is_favorite)},
        )

    async def save_as_saved_view(self, view_id: str, name: str | None = None) -> dict:
        """E92: POST /api/saved-views/{id}/save-as body {name?}."""
        body: dict = {}
        if name is not None:
            body["name"] = name
        return await self.post(f"/api/saved-views/{view_id}/save-as", data=body)

    # ============================================================================
    # Initiatives API
    # ============================================================================

    async def list_initiatives(self) -> dict:
        return await self.get("/api/initiatives")

    async def get_initiative(self, initiative_id: str) -> dict:
        return await self.get(f"/api/initiatives/{initiative_id}")

    async def create_initiative(self, name: str, **kwargs) -> dict:
        data = {"name": name, **kwargs}
        return await self.post("/api/initiatives", data=data)

    async def update_initiative(self, initiative_id: str, **kwargs) -> dict:
        return await self.patch(f"/api/initiatives/{initiative_id}", data=kwargs)

    async def delete_initiative(self, initiative_id: str) -> dict:
        return await self.delete(f"/api/initiatives/{initiative_id}")

    async def list_initiative_relations(self, initiative_id: str) -> dict:
        return await self.get(f"/api/initiatives/{initiative_id}/relations")

    async def add_initiative_relation(
        self, initiative_id: str, target_initiative_id: str, relation_type: str
    ) -> dict:
        return await self.post(
            f"/api/initiatives/{initiative_id}/relations",
            data={"targetInitiativeId": target_initiative_id, "type": relation_type},
        )

    async def remove_initiative_relation(self, initiative_id: str, relation_id: str) -> dict:
        return await self.delete(
            f"/api/initiatives/{initiative_id}/relations/{relation_id}"
        )

    async def set_initiative_projects(self, initiative_id: str, project_ids: list[str]) -> dict:
        """E90: PUT /api/initiatives/{id}/projects — full replace (empty clears; unknown → 400)."""
        return await self.put(
            f"/api/initiatives/{initiative_id}/projects",
            data={"projectIds": list(project_ids)},
        )

    async def attach_initiative_project(self, initiative_id: str, project_id: str) -> dict:
        """E90: POST /api/initiatives/{id}/projects/{project_id} — idempotent attach."""
        return await self.post(
            f"/api/initiatives/{initiative_id}/projects/{project_id}"
        )

    async def detach_initiative_project(self, initiative_id: str, project_id: str) -> dict:
        """E90: DELETE /api/initiatives/{id}/projects/{project_id}."""
        return await self.delete(
            f"/api/initiatives/{initiative_id}/projects/{project_id}"
        )

    # ========================================================================
    # Customers / Customer Requests (E22)
    # ========================================================================

    async def list_customers(self) -> dict:
        return await self.get("/api/customers")

    async def create_customer(self, name: str, **kwargs) -> dict:
        data = {"name": name, **kwargs}
        return await self.post("/api/customers", data=data)

    async def list_customer_requests(
        self,
        customer_id: str | None = None,
        status: str | None = None,
        issue_id: str | None = None,
    ) -> dict:
        params = {}
        if customer_id:
            params["customerId"] = customer_id
        if status:
            params["status"] = status
        if issue_id:
            params["issueId"] = issue_id
        return await self.get("/api/customer-requests", params=params or None)

    async def create_customer_request(self, customer_id: str, title: str, **kwargs) -> dict:
        data = {"customerId": customer_id, "title": title, **kwargs}
        return await self.post("/api/customer-requests", data=data)

    async def link_customer_request_issue(self, request_id: str, issue_id: str) -> dict:
        return await self.post(
            f"/api/customer-requests/{request_id}/issues",
            data={"issueId": issue_id},
        )

    async def get_customer_request(self, request_id: str, *, include_token: bool = False) -> dict:
        params = {"include_token": "1"} if include_token else None
        return await self.get(f"/api/customer-requests/{request_id}", params=params)

    async def enable_customer_request_status_link(
        self, request_id: str, *, public_replies_enabled: bool | None = None
    ) -> dict:
        body = {}
        if public_replies_enabled is not None:
            body["publicRepliesEnabled"] = public_replies_enabled
        return await self.post(
            f"/api/customer-requests/{request_id}/status-link/enable",
            data=body,
        )

    async def rotate_customer_request_status_link(self, request_id: str) -> dict:
        return await self.post(f"/api/customer-requests/{request_id}/status-link/rotate")

    async def revoke_customer_request_status_link(self, request_id: str) -> dict:
        return await self.post(f"/api/customer-requests/{request_id}/status-link/revoke")

    async def public_customer_request_status(self, token: str) -> dict:
        return await self.get(f"/api/public/customer-requests/{token}")


    # ========================================================================
    # Custom Fields (E25)
    # ========================================================================

    async def list_custom_fields(self, include_archived: bool = False) -> dict:
        params = {}
        if include_archived:
            params["includeArchived"] = "true"
        return await self.get("/api/custom-fields", params=params or None)

    async def create_custom_field(self, name: str, field_type: str, **kwargs) -> dict:
        data = {"name": name, "type": field_type, **kwargs}
        return await self.post("/api/custom-fields", data=data)

    async def update_custom_field(self, field_id: str, **kwargs) -> dict:
        return await self.patch(f"/api/custom-fields/{field_id}", data=kwargs)

    async def validate_formula(
        self, formula_expr: str, result_type: str | None = None
    ) -> dict:
        data = {"formulaExpr": formula_expr}
        if result_type:
            data["formulaResultType"] = result_type
        return await self.post("/api/custom-fields/validate-formula", data=data)

    async def reorder_custom_fields(self, ordered_ids: list[str]) -> dict:
        """E89: POST /api/custom-fields/reorder — soft update positions by orderedIds (unknown ids ignored)."""
        return await self.post(
            "/api/custom-fields/reorder",
            data={"orderedIds": list(ordered_ids)},
        )

    async def set_issue_custom_fields(self, issue_id: str, values: list[dict]) -> dict:
        return await self.patch(
            f"/api/issues/{issue_id}/custom-fields",
            data={"values": values},
        )

    # ========================================================================
    # Insights (E24)
    # ========================================================================


    async def list_automations(self) -> dict:
        return await self.get("/api/automations")

    async def create_automation(
        self,
        name: str,
        trigger_type: str,
        action_type: str,
        *,
        trigger_config: dict | None = None,
        action_config: dict | None = None,
        condition: dict | None = None,
        enabled: bool = True,
    ) -> dict:
        data = {
            "name": name,
            "triggerType": trigger_type,
            "actionType": action_type,
            "triggerConfig": trigger_config or {},
            "actionConfig": action_config or {},
            "enabled": enabled,
        }
        if condition is not None:
            data["condition"] = condition
        return await self.post("/api/automations", data=data)

    async def enable_automation(self, rule_id: str) -> dict:
        return await self.post(f"/api/automations/{rule_id}/enable")

    async def disable_automation(self, rule_id: str) -> dict:
        return await self.post(f"/api/automations/{rule_id}/disable")

    async def update_automation(self, rule_id: str, payload: dict) -> dict:
        return await self.patch(f"/api/automations/{rule_id}", data=payload)

    async def run_due_automations(self) -> dict:
        return await self.post("/api/automations/run-due")

    async def list_automation_pending(self, status: str = "pending") -> dict:
        return await self.get("/api/automations/pending", params={"status": status})


    # ========================================================================
    # Outbound Webhooks (E29)
    # ========================================================================

    async def list_webhooks(self) -> dict:
        return await self.get("/api/webhooks")

    async def create_webhook(
        self,
        url: str,
        events: list,
        *,
        name: str | None = None,
        enabled: bool = True,
    ) -> dict:
        data = {"url": url, "events": events, "enabled": enabled}
        if name is not None:
            data["name"] = name
        return await self.post("/api/webhooks", data=data)

    async def update_webhook(self, webhook_id: str, body: dict) -> dict:
        return await self.patch(f"/api/webhooks/{webhook_id}", data=body)

    async def delete_webhook(self, webhook_id: str) -> dict:
        return await self.delete(f"/api/webhooks/{webhook_id}")

    async def test_webhook(self, webhook_id: str) -> dict:
        return await self.post(f"/api/webhooks/{webhook_id}/test")

    async def get_webhook(self, webhook_id: str) -> dict:
        return await self.get(f"/api/webhooks/{webhook_id}")

    async def retry_webhook_delivery(self, webhook_id: str, delivery_log_id: str) -> dict:
        return await self.post(
            f"/api/webhooks/{webhook_id}/deliveries/{delivery_log_id}/retry"
        )

    async def run_due_webhook_deliveries(self) -> dict:
        return await self.post("/api/webhooks/run-due-deliveries")

    async def get_webhook_stats(
        self, *, window: str | None = None, webhook_id: str | None = None
    ) -> dict:
        params: dict = {}
        if window:
            params["window"] = window
        if webhook_id:
            return await self.get(f"/api/webhooks/{webhook_id}/stats", params=params or None)
        return await self.get("/api/webhooks/stats", params=params or None)

    async def list_webhook_dead_letter(
        self,
        *,
        webhook_id: str | None = None,
        event: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict:
        params: dict = {}
        if webhook_id:
            params["webhook_id"] = webhook_id
        if event:
            params["event"] = event
        if limit is not None:
            params["limit"] = limit
        if cursor:
            params["cursor"] = cursor
        return await self.get("/api/webhooks/dead-letter", params=params or None)

    async def bulk_retry_webhook_dead_letter(self, delivery_log_ids: list) -> dict:
        return await self.post(
            "/api/webhooks/dead-letter/retry",
            data={"deliveryLogIds": list(delivery_log_ids)},
        )

    async def get_webhook_alert_settings(self, webhook_id: str | None = None) -> dict:
        params: dict = {}
        if webhook_id:
            params["webhook_id"] = webhook_id
        return await self.get("/api/webhooks/alerts", params=params or None)

    async def set_webhook_alert_settings(
        self, settings: dict, *, webhook_id: str | None = None
    ) -> dict:
        body: dict = {"settings": settings}
        if webhook_id:
            body["webhookId"] = webhook_id
        return await self.patch("/api/webhooks/alerts", data=body)

    async def mute_webhook_alerts(
        self, until: str, *, webhook_id: str | None = None
    ) -> dict:
        body: dict = {"until": until}
        if webhook_id:
            body["webhookId"] = webhook_id
        return await self.post("/api/webhooks/alerts/mute", data=body)

    async def unmute_webhook_alerts(self, webhook_id: str | None = None) -> dict:
        params: dict = {}
        if webhook_id:
            params["webhook_id"] = webhook_id
        return await self.post("/api/webhooks/alerts/unmute", params=params or None)

    async def run_webhook_alert_eval(self) -> dict:
        return await self.post("/api/webhooks/run-alert-eval")



    # ========================================================================
    # Issue Forms (E31)
    # ========================================================================

    async def list_forms(self) -> dict:
        return await self.get("/api/forms")

    async def get_form(self, form_id: str) -> dict:
        return await self.get(f"/api/forms/{form_id}")

    async def create_form(
        self,
        name: str,
        fields: list,
        *,
        description: str | None = None,
        slug: str | None = None,
        enabled: bool = True,
        create_customer_request: bool = False,
        enqueue_triage: bool = False,
    ) -> dict:
        data = {
            "name": name,
            "fields": fields,
            "enabled": enabled,
            "createCustomerRequest": create_customer_request,
            "enqueueTriage": enqueue_triage,
        }
        if description is not None:
            data["description"] = description
        if slug is not None:
            data["slug"] = slug
        return await self.post("/api/forms", data=data)

    async def update_form(self, form_id: str, body: dict) -> dict:
        return await self.patch(f"/api/forms/{form_id}", data=body)

    async def delete_form(self, form_id: str) -> dict:
        return await self.delete(f"/api/forms/{form_id}")

    async def regenerate_form_token(self, form_id: str) -> dict:
        return await self.post(f"/api/forms/{form_id}/regenerate-token")


    # ========================================================================
    # Notification preferences (E27)
    # ========================================================================

    async def get_notif_prefs(self) -> dict:
        return await self.get("/api/inbox/preferences")

    async def put_notif_prefs(self, updates: dict) -> dict:
        return await self.put("/api/inbox/preferences", data=updates)

    async def notif_email_test(self) -> dict:
        return await self.post("/api/inbox/email-test")


    async def run_due_reminders(self) -> dict:
        return await self.post("/api/inbox/run-due-reminders")

    async def list_due_reminder_deliveries(self, bucket_date: str | None = None) -> dict:
        params = {}
        if bucket_date:
            params["bucket_date"] = bucket_date
        return await self.get("/api/inbox/due-reminder-deliveries", params=params or None)


    async def insights_summary(
        self,
        cycle_id: str | None = None,
        assignee_limit: int | None = None,
        project_id: str | None = None,
        label_id: int | None = None,
        label_ids: list[int] | None = None,
    ) -> dict:
        params = {}
        if cycle_id:
            params["cycleId"] = cycle_id
        if assignee_limit is not None:
            params["assigneeLimit"] = assignee_limit
        if project_id:
            params["projectId"] = project_id
        if label_ids:
            params["labelIds"] = ",".join(str(x) for x in label_ids)
        elif label_id is not None:
            params["labelId"] = label_id
        return await self.get("/api/insights/summary", params=params or None)

    async def insights_export(
        self,
        cycle_id: str | None = None,
        project_id: str | None = None,
        label_id: int | None = None,
        label_ids: list[int] | None = None,
    ) -> bytes:
        """E55/E59: download insights CSV for current workspace."""
        import httpx
        url = f"{self.base_url}/api/insights/export.csv"
        headers = self._get_headers()
        params = {}
        if cycle_id:
            params["cycleId"] = cycle_id
        if project_id:
            params["projectId"] = project_id
        if label_ids:
            params["labelIds"] = ",".join(str(x) for x in label_ids)
        elif label_id is not None:
            params["labelId"] = label_id
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params or None, headers=headers)
            if response.status_code >= 400:
                raise APIError(response.status_code, response.text)
            return response.content

    async def insights_reports_list(self) -> dict:
        return await self.get("/api/insights/reports")

    async def insights_reports_create(
        self,
        *,
        name: str,
        filters: dict | None = None,
        is_default: bool = False,
        visibility: str = "personal",
    ) -> dict:
        return await self.post(
            "/api/insights/reports",
            data={
                "name": name,
                "filters": filters or {},
                "isDefault": bool(is_default),
                "visibility": visibility or "personal",
            },
        )

    async def insights_reports_set_visibility(self, report_id: str, visibility: str) -> dict:
        return await self.patch(
            f"/api/insights/reports/{report_id}",
            data={"visibility": visibility},
        )

    async def insights_reports_fork(self, report_id: str, *, name: str | None = None) -> dict:
        body = {"name": name} if name else {}
        return await self.post(f"/api/insights/reports/{report_id}/fork", data=body)

    async def insights_reports_delete(self, report_id: str) -> dict:
        return await self.delete(f"/api/insights/reports/{report_id}")

    async def insights_run_digest(self) -> dict:
        return await self.post("/api/insights/run-digest")



    # ========================================================================
    # Issue Recurrences (E35)
    # ========================================================================

    async def list_recurrences(self) -> dict:
        return await self.get("/api/recurrences")

    async def get_recurrence(self, recurrence_id: str) -> dict:
        return await self.get(f"/api/recurrences/{recurrence_id}")

    async def create_recurrence(self, body: dict) -> dict:
        return await self.post("/api/recurrences", data=body)

    async def update_recurrence(self, recurrence_id: str, body: dict) -> dict:
        return await self.patch(f"/api/recurrences/{recurrence_id}", data=body)

    async def delete_recurrence(self, recurrence_id: str) -> dict:
        return await self.delete(f"/api/recurrences/{recurrence_id}")

    async def run_due_recurrences(self) -> dict:
        return await self.post("/api/recurrences/run-due")


    async def list_sla_policies(self) -> dict:
        return await self.get("/api/sla/policies")

    async def create_sla_policy(self, body: dict) -> dict:
        return await self.post("/api/sla/policies", data=body)

    async def update_sla_policy(self, policy_id: str, body: dict) -> dict:
        return await self.patch(f"/api/sla/policies/{policy_id}", data=body)

    async def delete_sla_policy(self, policy_id: str) -> dict:
        return await self.delete(f"/api/sla/policies/{policy_id}")

    async def get_issue_sla(self, issue_id: str) -> dict:
        return await self.get(f"/api/issues/{issue_id}/sla")

    async def run_due_sla(self) -> dict:
        return await self.post("/api/sla/run-due")

    async def list_holiday_packs(
        self, *, region: str | None = None, year: int | None = None
    ) -> dict:
        params: dict = {}
        if region:
            params["region"] = region
        if year is not None:
            params["year"] = year
        return await self.get("/api/sla/holiday-packs", params=params or None)

    async def get_holiday_pack(self, region: str, year: int) -> dict:
        return await self.get(f"/api/sla/holiday-packs/{region}/{year}")

    async def preview_holiday_pack(
        self, region: str, year: int, *, target: str = "workspace", policy_id: str | None = None
    ) -> dict:
        body: dict = {"target": target}
        if policy_id:
            body["policyId"] = policy_id
        return await self.post(f"/api/sla/holiday-packs/{region}/{year}/preview", data=body)

    async def apply_holiday_pack(
        self, region: str, year: int, *, target: str = "workspace", policy_id: str | None = None
    ) -> dict:
        body: dict = {"target": target}
        if policy_id:
            body["policyId"] = policy_id
        return await self.post(f"/api/sla/holiday-packs/{region}/{year}/apply", data=body)

    # ============================================================================
    # Entity Documents API
    # ============================================================================

    async def list_entity_docs(self, parent_type: str, parent_id: str) -> dict:
        return await self.get(
            "/api/entity-documents",
            params={"parentType": parent_type, "parentId": parent_id},
        )

    async def get_entity_doc(self, doc_id: str) -> dict:
        return await self.get(f"/api/entity-documents/{doc_id}")

    async def create_entity_doc(
        self, parent_type: str, parent_id: str, title: str, body_md: str = ""
    ) -> dict:
        return await self.post(
            "/api/entity-documents",
            data={
                "parentType": parent_type,
                "parentId": parent_id,
                "title": title,
                "bodyMd": body_md,
            },
        )

    async def update_entity_doc(self, doc_id: str, **kwargs) -> dict:
        body = {}
        if "title" in kwargs and kwargs["title"] is not None:
            body["title"] = kwargs["title"]
        if "body_md" in kwargs and kwargs["body_md"] is not None:
            body["bodyMd"] = kwargs["body_md"]
        if "bodyMd" in kwargs and kwargs["bodyMd"] is not None:
            body["bodyMd"] = kwargs["bodyMd"]
        return await self.patch(f"/api/entity-documents/{doc_id}", data=body)

    async def delete_entity_doc(self, doc_id: str) -> dict:
        return await self.delete(f"/api/entity-documents/{doc_id}")

    # ============================================================================
    # Issue relations / children
    # ============================================================================

    async def list_issue_children(self, issue_id: str) -> dict:
        return await self.get(f"/api/issues/{issue_id}/children")

    async def list_issue_relations(self, issue_id: str) -> dict:
        return await self.get(f"/api/issues/{issue_id}/relations")

    async def add_issue_relation(self, issue_id: str, target_id: str, relation_type: str) -> dict:
        return await self.post(
            f"/api/issues/{issue_id}/relations",
            params={"target_id": target_id, "relation_type": relation_type},
        )

    async def remove_issue_relation(self, issue_id: str, target_id: str, relation_type: str) -> dict:
        return await self.delete(
            f"/api/issues/{issue_id}/relations",
            params={"target_id": target_id, "relation_type": relation_type},
        )

    # ============================================================================
    # Project API
    # ============================================================================


    async def list_projects(self, active_only: bool = True) -> dict:
        """List all projects.

        Returns:
            Dict with pagination: {"rows": [...], "total": N}
        """
        data = await self.get("/api/projects", params={"active_only": active_only})
        # Handle both list and dict responses
        if isinstance(data, list):
            return {"rows": data, "total": len(data)}
        return data

    async def get_project(self, project_id: str) -> dict | None:
        """Get project details."""
        return await self.get(f"/api/projects/{project_id}")

    async def create_project(
        self,
        name: str,
        description: str = "",
        template_id: str | None = None,
        starts_at: str | None = None,
    ) -> dict:
        """Create a new project (E72: optional template_id seeds milestones)."""
        data: dict = {"name": name, "description": description}
        if template_id:
            data["template_id"] = template_id
        if starts_at:
            data["starts_at"] = starts_at
        return await self.post("/api/projects", data=data)

    async def list_project_templates(self) -> dict:
        return await self.get("/api/project-templates")

    async def get_project_template(self, template_id: str) -> dict:
        return await self.get(f"/api/project-templates/{template_id}")

    async def create_project_template(
        self,
        *,
        name: str,
        description: str | None = None,
        icon: str | None = None,
        payload: dict | None = None,
        sort_order: int = 0,
    ) -> dict:
        body: dict = {"name": name, "sortOrder": sort_order}
        if description is not None:
            body["description"] = description
        if icon is not None:
            body["icon"] = icon
        if payload is not None:
            body["payload"] = payload
        return await self.post("/api/project-templates", data=body)

    async def update_project_template(
        self,
        template_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        payload: dict | None = None,
        sort_order: int | None = None,
    ) -> dict:
        body: dict = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if icon is not None:
            body["icon"] = icon
        if payload is not None:
            body["payload"] = payload
        if sort_order is not None:
            body["sortOrder"] = sort_order
        return await self.patch(f"/api/project-templates/{template_id}", data=body)

    async def delete_project_template(self, template_id: str) -> dict:
        return await self.delete(f"/api/project-templates/{template_id}")

    async def apply_project_template(
        self,
        template_id: str,
        *,
        name: str,
        description: str | None = None,
        starts_at: str | None = None,
    ) -> dict:
        body: dict = {"name": name}
        if description is not None:
            body["description"] = description
        if starts_at is not None:
            body["startsAt"] = starts_at
        return await self.post(f"/api/project-templates/{template_id}/apply", data=body)

    async def project_template_from_project(
        self,
        project_id: str,
        *,
        name: str,
        description: str | None = None,
        icon: str | None = None,
    ) -> dict:
        body: dict = {"name": name}
        if description is not None:
            body["description"] = description
        if icon is not None:
            body["icon"] = icon
        return await self.post(
            f"/api/project-templates/from-project/{project_id}", data=body
        )

    async def update_project(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        lead_id: str | None | object = ...,
    ) -> dict:
        """Update project (E79: lead_id; pass None to clear)."""
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if lead_id is not ...:
            data["lead_id"] = lead_id
        # Prefer PATCH when lead_id present (E79); PUT remains compatible
        if "lead_id" in data and name is None and description is None:
            return await self.patch(f"/api/projects/{project_id}", data=data)
        return await self.put(f"/api/projects/{project_id}", data=data)

    async def list_project_members(self, project_id: str) -> list | dict:
        """E79: list project roster members."""
        return await self.get(f"/api/projects/{project_id}/members")

    async def list_project_milestones(
        self, project_id: str, *, status: str | None = None
    ) -> list | dict:
        """E81: GET /api/projects/{id}/milestones"""
        params = {}
        if status:
            params["status"] = status
        return await self.get(
            f"/api/projects/{project_id}/milestones",
            params=params or None,
        )

    async def create_project_milestone(self, project_id: str, **kwargs) -> dict:
        """E81: POST /api/projects/{id}/milestones"""
        return await self.post(f"/api/projects/{project_id}/milestones", data=kwargs)

    async def get_project_milestone(self, project_id: str, milestone_id: str) -> dict:
        """E81: GET /api/projects/{id}/milestones/{milestone_id}"""
        return await self.get(f"/api/projects/{project_id}/milestones/{milestone_id}")

    async def update_project_milestone(
        self, project_id: str, milestone_id: str, **kwargs
    ) -> dict:
        """E81: PATCH /api/projects/{id}/milestones/{milestone_id}"""
        return await self.patch(
            f"/api/projects/{project_id}/milestones/{milestone_id}", data=kwargs
        )

    async def delete_project_milestone(self, project_id: str, milestone_id: str) -> bool:
        """E81: DELETE /api/projects/{id}/milestones/{milestone_id}"""
        await self.delete(f"/api/projects/{project_id}/milestones/{milestone_id}")
        return True

    async def list_project_repos(self, project_id: str) -> list | dict:
        """E95: GET /api/projects/{id}/repos"""
        return await self.get(f"/api/projects/{project_id}/repos")

    async def get_project_repo(self, project_id: str, repo_id: str | int) -> dict:
        """E95: GET /api/projects/{id}/repos/{repo_id}"""
        return await self.get(f"/api/projects/{project_id}/repos/{repo_id}")

    async def create_project_repo(
        self,
        project_id: str,
        *,
        name: str,
        url: str,
        main_branch: str = "main",
    ) -> dict:
        """E95: POST /api/projects/{id}/repos body {name,url,main_branch,project_id}"""
        return await self.post(
            f"/api/projects/{project_id}/repos",
            data={
                "name": name,
                "url": url,
                "main_branch": main_branch,
                "project_id": project_id,
            },
        )

    async def update_project_repo(
        self, project_id: str, repo_id: str | int, **fields
    ) -> dict:
        """E95: PUT /api/projects/{id}/repos/{repo_id} body 仅提供字段"""
        return await self.put(
            f"/api/projects/{project_id}/repos/{repo_id}",
            data=fields,
        )

    async def delete_project_repo(self, project_id: str, repo_id: str | int) -> bool:
        """E95: DELETE /api/projects/{id}/repos/{repo_id}"""
        await self.delete(f"/api/projects/{project_id}/repos/{repo_id}")
        return True


    async def add_project_member(self, project_id: str, user_id: str) -> dict:
        """E79: add project roster member."""
        return await self.post(
            f"/api/projects/{project_id}/members", data={"user_id": user_id}
        )

    async def remove_project_member(self, project_id: str, user_id: str) -> dict | bool:
        """E79: remove project roster member."""
        return await self.delete(f"/api/projects/{project_id}/members/{user_id}")

    async def delete_project(self, project_id: str) -> bool:
        """Delete project."""
        await self.delete(f"/api/projects/{project_id}")
        return True

    # ============================================================================
    # Issue API
    # ============================================================================


    async def export_issues_csv(self, params: dict | None = None) -> bytes:
        """E28: download issues CSV for current workspace."""
        import httpx
        url = f"{self.base_url}/api/issues/export.csv"
        headers = self._get_headers()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params or {}, headers=headers)
            if response.status_code >= 400:
                raise APIError(response.status_code, response.text)
            return response.content

    async def get_issue_timeline(self, issue_id: str, limit: int = 50) -> dict:
        """E41: list issue timeline."""
        return await self.get(f"/api/issues/{issue_id}/timeline", params={"limit": limit})

    async def export_issue_timeline_csv(
        self, issue_id: str, params: dict | None = None
    ) -> bytes:
        """E41: download single-issue timeline CSV."""
        import httpx
        url = f"{self.base_url}/api/issues/{issue_id}/timeline/export.csv"
        headers = self._get_headers()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params or {}, headers=headers)
            if response.status_code >= 400:
                raise APIError(response.status_code, response.text)
            return response.content

    async def list_workspace_activity(self, params: dict | None = None) -> dict:
        """E47: workspace activity feed (JSON cursor)."""
        return await self.get("/api/issues/activity", params=params or {})

    async def activity_unread_count(self, params: dict | None = None) -> dict:
        """E52: activity unread-count (thin bell)."""
        return await self.get("/api/issues/activity/unread-count", params=params or {"watching": True})

    async def export_workspace_timeline_csv(self, params: dict | None = None) -> bytes:
        """E41: download workspace timeline CSV."""
        import httpx
        url = f"{self.base_url}/api/issues/timeline/export.csv"
        headers = self._get_headers()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params or {}, headers=headers)
            if response.status_code >= 400:
                raise APIError(response.status_code, response.text)
            return response.content

    async def import_issues_csv(self, file_path: str) -> dict:
        """E28: upload CSV to import issues."""
        import httpx
        import os
        url = f"{self.base_url}/api/issues/import"
        headers = self._get_headers()
        headers.pop("Content-Type", None)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        filename = os.path.basename(file_path)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "text/csv")}
                response = await client.post(url, files=files, headers=headers)
                return self._handle_response(response)

    async def list_issues(
        self,
        page: int = 1,
        page_size: int = 20,
        type: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        project_id: str | None = None,
        assignee_id: str | None = None,
        reporter_id: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        # Advanced filters
        recent: bool = False,
        updated_today: bool = False,
        overdue: bool = False,
        unassigned: bool = False,
        watching: bool = False,
        due_soon: bool = False,
        due_before: str | None = None,
        start_before: str | None = None,
        start_after: str | None = None,
        cycle_id: str | None = None,
        milestone_id: str | None = None,
        cf: list[str] | None = None,
        include: str | None = None,
    ) -> dict:
        """List issues with filtering.

        Args:
            page: Page number (default: 1)
            page_size: Page size (default: 20)
            type: Filter by issue type
            status: Filter by status
            priority: Filter by priority
            project_id: Filter by project ID
            assignee_id: Filter by assignee ID
            search: Search keyword
            sort_by: Sort field (default: created_at)
            sort_order: Sort order (asc/desc)
            recent: Filter issues created in last 7 days
            updated_today: Filter issues updated today
            overdue: Filter overdue issues (due_date < today AND status IN (open, in_progress))
            unassigned: Filter unassigned issues (assignee_id IS NULL)
        """
        params = {
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        if type:
            params["type"] = type
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority
        if project_id:
            params["project_id"] = project_id
        if assignee_id:
            params["assignee_id"] = assignee_id
        if reporter_id:
            params["reporter_id"] = reporter_id
        if search:
            params["search"] = search
        if recent:
            params["recent"] = "true"
        if updated_today:
            params["updated_today"] = "true"
        if overdue:
            params["overdue"] = "true"
        if unassigned:
            params["unassigned"] = "true"
        if watching:
            params["watching"] = "true"
        if due_soon:
            params["due_soon"] = "true"
        if due_before:
            params["due_before"] = due_before
        if start_before:
            params["start_before"] = start_before
        if start_after:
            params["start_after"] = start_after
        if cycle_id:
            params["cycle_id"] = cycle_id
        if milestone_id:
            params["milestone_id"] = milestone_id
        if include:
            params["include"] = include
        # E32: --cf key=value → cf.<key>=value (httpx MultiDict via list of tuples)
        if cf:
            items = [(k, params[k]) for k in params]
            for raw in cf:
                if "=" not in raw:
                    continue
                key, _, val = raw.partition("=")
                key = key.strip()
                if key:
                    items.append((f"cf.{key}", val))
            return await self.get("/api/issues", params=items)
        return await self.get("/api/issues", params=params)

    async def get_issue(
        self, issue_id: str, by_code: bool = False, include_deleted: bool = False
    ) -> dict:
        """Get issue details.

        Args:
            issue_id: Issue ID or issue code
            by_code: If True, query by issue_code; otherwise by ID (default)
            include_deleted: E77 — include soft-deleted (trash detail / restore by code)
        """
        params: dict = {}
        if by_code:
            params["by_code"] = "true"
        if include_deleted:
            params["include_deleted"] = "true"
        return await self.get(f"/api/issues/{issue_id}", params=params)

    async def get_issue_branch_name(self, issue_id: str) -> dict:
        """GET /api/issues/{id}/vcs/branch-name — same contract as FE."""
        return await self.get(f"/api/issues/{issue_id}/vcs/branch-name")

    async def list_issue_vcs_links(self, issue_id: str) -> dict:
        return await self.get(f"/api/issues/{issue_id}/vcs/links")

    async def create_issue_vcs_link(self, issue_id: str, **kwargs) -> dict:
        """POST link; kwargs use camelCase keys (kind, branchName, prUrl, ...)."""
        return await self.post(f"/api/issues/{issue_id}/vcs/links", data=kwargs)

    async def delete_issue_vcs_link(self, issue_id: str, link_id: str) -> dict:
        return await self.delete(f"/api/issues/{issue_id}/vcs/links/{link_id}")


    async def list_issue_templates(self) -> dict:
        """E82: GET /api/issue-templates"""
        return await self.get("/api/issue-templates")

    async def get_issue_template(self, template_id: str) -> dict:
        """E82: GET /api/issue-templates/{id}"""
        return await self.get(f"/api/issue-templates/{template_id}")

    async def create_issue_template(
        self,
        *,
        name: str,
        description: str | None = None,
        icon: str | None = None,
        payload: dict | None = None,
        sort_order: int = 0,
    ) -> dict:
        """E82: POST /api/issue-templates"""
        body: dict = {"name": name, "sortOrder": sort_order}
        if description is not None:
            body["description"] = description
        if icon is not None:
            body["icon"] = icon
        if payload is not None:
            body["payload"] = payload
        return await self.post("/api/issue-templates", data=body)

    async def update_issue_template(
        self,
        template_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        payload: dict | None = None,
        sort_order: int | None = None,
    ) -> dict:
        """E82: PATCH /api/issue-templates/{id}"""
        body: dict = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if icon is not None:
            body["icon"] = icon
        if payload is not None:
            body["payload"] = payload
        if sort_order is not None:
            body["sortOrder"] = sort_order
        return await self.patch(f"/api/issue-templates/{template_id}", data=body)

    async def delete_issue_template(self, template_id: str) -> dict:
        """E82: DELETE /api/issue-templates/{id}"""
        return await self.delete(f"/api/issue-templates/{template_id}")

    async def seed_issue_templates(self) -> dict:
        """E82: POST /api/issue-templates/seed"""
        return await self.post("/api/issue-templates/seed", data={})

    async def create_issue(
        self,
        title: str,
        description: str = "",
        type: str = "feature",
        status: str = "open",
        priority: str = "medium",
        project_id: str | None = None,
        assignee_id: str | None = None,
        assignee_ids: list[str] | None = None,
        estimate_points: float | None = None,
        start_date: str | None = None,
        due_date: str | None = None,
        milestone_id: str | None = None,
        template_id: str | None = None,
    ) -> dict:
        """Create a new issue.

        Reporter is automatically set by backend from JWT token.
        E82: optional template_id merges template payload.
        """
        # Normalize priority to API format
        normalized_priority = _normalize_priority(priority)

        data = {
            "title": title,
            "description": description,
            "type": type,
            "status": status,
            "priority": normalized_priority,
        }
        if project_id:
            data["project_id"] = project_id
        if assignee_ids:
            data["assignee_ids"] = assignee_ids
        elif assignee_id:
            data["assignee_id"] = assignee_id
        if estimate_points is not None:
            data["estimate_points"] = estimate_points
        if start_date:
            data["start_date"] = start_date
        if due_date:
            data["due_date"] = due_date
        if milestone_id:
            data["milestone_id"] = milestone_id
        if template_id:
            data["template_id"] = template_id

        return await self.post("/api/issues", data=data)

    async def duplicate_issue(
        self,
        issue_id: str,
        *,
        title: str | None = None,
        project_id: str | None = None,
        cycle_id: str | None = None,
        parent_issue_id: str | None = None,
        assignee_ids: list[str] | None = None,
    ) -> dict:
        """E75: POST /api/issues/{id}/duplicate — Linear-style copy."""
        data: dict = {}
        if title is not None:
            data["title"] = title
        if project_id is not None:
            data["project_id"] = project_id
        if cycle_id is not None:
            data["cycle_id"] = cycle_id
        if parent_issue_id is not None:
            data["parent_issue_id"] = parent_issue_id
        if assignee_ids is not None:
            data["assignee_ids"] = assignee_ids
        return await self.post(f"/api/issues/{issue_id}/duplicate", data=data)

    async def list_issue_trash(self, *, page: int = 1, page_size: int = 20) -> dict:
        """E77: GET /api/issues/trash"""
        return await self.get(
            "/api/issues/trash",
            params={"page": page, "page_size": page_size},
        )

    async def restore_issue(self, issue_id: str) -> dict:
        """E77: POST /api/issues/{id}/restore"""
        return await self.post(f"/api/issues/{issue_id}/restore", data={})


    async def list_issue_links(self, issue_id: str) -> dict:
        """E76: GET /api/issues/{id}/links"""
        data = await self.get(f"/api/issues/{issue_id}/links")
        return data if isinstance(data, dict) else {"rows": data or [], "total": 0}

    async def create_issue_link(
        self, issue_id: str, url: str, *, title: str | None = None
    ) -> dict:
        """E76: POST /api/issues/{id}/links"""
        body: dict = {"url": url}
        if title is not None:
            body["title"] = title
        return await self.post(f"/api/issues/{issue_id}/links", data=body)

    async def update_issue_link(
        self,
        issue_id: str,
        link_id: str,
        *,
        url: str | None = None,
        title: str | None = None,
        position: int | None = None,
    ) -> dict:
        """E76: PATCH /api/issues/{id}/links/{link_id}"""
        body: dict = {}
        if url is not None:
            body["url"] = url
        if title is not None:
            body["title"] = title
        if position is not None:
            body["position"] = position
        return await self.patch(f"/api/issues/{issue_id}/links/{link_id}", data=body)

    async def delete_issue_link(self, issue_id: str, link_id: str) -> dict:
        """E76: DELETE /api/issues/{id}/links/{link_id}"""
        return await self.delete(f"/api/issues/{issue_id}/links/{link_id}")


    async def update_issue(self, issue_id: str, **kwargs) -> dict:
        """Update issue.

        Automatically converts CLI enum values to API format:
        - priority: lowercase (already lowercase, no conversion needed)
        """
        # Normalize priority to API format
        if "priority" in kwargs and kwargs["priority"]:
            kwargs["priority"] = _normalize_priority(kwargs["priority"])

        return await self.put(f"/api/issues/{issue_id}", data=kwargs)

    async def delete_issue(self, issue_id: str) -> bool:
        """Delete issue."""
        await self.delete(f"/api/issues/{issue_id}")
        return True

    async def get_issues_by_ids(self, issue_ids: list[str]) -> dict:
        """Batch get issues by IDs.

        Args:
            issue_ids: List of issue IDs (max 100)

        Returns:
            Response with issues list
        """
        return await self.post("/api/issues/batch", data={
            "ids": issue_ids
        })

    async def bulk_update_issues(self, payload: dict) -> dict:
        """E20: POST /api/issues/bulk/update (requires X-Workspace-Id)."""
        return await self.post("/api/issues/bulk/update", data=payload)

    async def move_issue_on_board(
        self,
        issue_id: str,
        status: str,
        position: int,
        ordered_ids: list[str] | None = None,
    ) -> dict:
        """E91: POST /api/issues/board/move — atomic status+position; optional ordered_ids.

        Body uses snake_case keys (issue_id/status/position/ordered_ids) to match BE/FE.
        """
        body: dict = {
            "issue_id": issue_id,
            "status": status,
            "position": int(position),
        }
        if ordered_ids is not None:
            body["ordered_ids"] = list(ordered_ids)
        return await self.post("/api/issues/board/move", data=body)

    async def update_issue_status(self, issue_id: str, status: str) -> dict:
        """Quick update issue status."""
        return await self.put(f"/api/issues/{issue_id}/status", params={"status": status})

    async def update_issue_assignee(self, issue_id: str, assignee_id: str | None) -> dict:
        """Quick update issue assignee."""
        return await self.put(f"/api/issues/{issue_id}/assignee", params={"assignee_id": assignee_id})

    async def update_issue_priority(self, issue_id: str, priority: str) -> dict:
        """Quick update issue priority."""
        return await self.put(f"/api/issues/{issue_id}/priority", params={"priority": priority})

    async def add_comment(self, issue_id: str, content: str, parent_id: str | None = None) -> dict:
        """Add comment to issue (E74: optional parent_id for depth-1 reply)."""
        payload: dict = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id
        return await self.post(f"/api/issues/{issue_id}/comments", data=payload)

    async def get_comments(self, issue_id: str) -> list[dict]:
        """Get issue comments.

        Returns:
            List of comment dictionaries
        """
        data = await self.get(f"/api/issues/{issue_id}/comments")
        rows = data.get("rows", []) if isinstance(data, dict) else data
        return rows if isinstance(rows, list) else []

    async def delete_comment(self, comment_id: str) -> bool:
        """Delete a comment."""
        await self.delete(f"/api/issues/comments/{comment_id}")
        return True

    # ============================================================================
    # Issue / Comment Reactions API (E94)
    # ============================================================================

    async def list_issue_reactions(self, issue_id: str) -> dict:
        """E94: GET /api/issues/{id}/reactions → {rows,total}."""
        return await self.get(f"/api/issues/{issue_id}/reactions")

    async def add_issue_reaction(self, issue_id: str, emoji: str) -> dict:
        """E94: POST /api/issues/{id}/reactions body {emoji}."""
        return await self.post(
            f"/api/issues/{issue_id}/reactions",
            data={"emoji": emoji},
        )

    async def remove_issue_reaction(self, issue_id: str, emoji: str) -> dict:
        """E94: DELETE /api/issues/{id}/reactions?emoji=."""
        return await self.delete(
            f"/api/issues/{issue_id}/reactions",
            params={"emoji": emoji},
        )

    async def list_comment_reactions(self, issue_id: str, comment_id: str) -> dict:
        """E94: GET /api/issues/{id}/comments/{cid}/reactions → {reactions}."""
        return await self.get(
            f"/api/issues/{issue_id}/comments/{comment_id}/reactions"
        )

    async def add_comment_reaction(
        self, issue_id: str, comment_id: str, emoji: str
    ) -> dict:
        """E94: POST …/comments/{cid}/reactions body {emoji}."""
        return await self.post(
            f"/api/issues/{issue_id}/comments/{comment_id}/reactions",
            data={"emoji": emoji},
        )

    async def remove_comment_reaction(
        self, issue_id: str, comment_id: str, emoji: str
    ) -> dict:
        """E94: DELETE …/comments/{cid}/reactions?emoji=."""
        return await self.delete(
            f"/api/issues/{issue_id}/comments/{comment_id}/reactions",
            params={"emoji": emoji},
        )

    # ============================================================================
    # Issue Document API
    # ============================================================================

    async def get_issue_documents(self, issue_id: str) -> list:
        """Get issue documents (attachments)."""
        data = await self.get(f"/api/issues/{issue_id}/attachments")
        return data if isinstance(data, list) else []

    async def upload_issue_document(
        self,
        issue_id: str,
        file_path: str,
        description: str | None = None
    ) -> dict:
        """Upload document to issue.

        Args:
            issue_id: Issue ID
            file_path: Path to file to upload
            description: Optional description

        Returns:
            Uploaded document info
        """
        import httpx
        import os

        url = f"{self.base_url}/api/issues/{issue_id}/attachments"
        headers = self._get_headers()
        # Remove Content-Type to let httpx set multipart/form-data
        headers.pop("Content-Type", None)

        # Check file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get filename from path
        filename = os.path.basename(file_path)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "application/octet-stream")}
                data = {}
                if description:
                    data["description"] = description

                response = await client.post(
                    url,
                    files=files,
                    data=data,
                    headers=headers
                )
                return self._handle_response(response)

    async def delete_issue_document(self, issue_id: str, document_id: str) -> bool:
        """Delete issue document."""
        await self.delete(f"/api/issues/{issue_id}/attachments/{document_id}")
        return True

    async def download_issue_document(self, issue_id: str, document_id: str, save_path: str) -> str:
        """Download issue document.

        Args:
            issue_id: Issue ID
            document_id: Document ID
            save_path: Path to save the downloaded file

        Returns:
            Path where file was saved
        """
        import httpx
        import os

        url = f"{self.base_url}/api/issues/{issue_id}/attachments/{document_id}/download"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)

            if response.status_code >= 400:
                raise APIError(f"Download failed: HTTP {response.status_code}", response.status_code)

            # Get filename from Content-Disposition header or use save_path
            content_disposition = response.headers.get("content-disposition", "")
            filename = None

            if content_disposition and "filename=" in content_disposition:
                # Parse filename from header (handles UTF-8 encoding)
                import urllib.parse
                for part in content_disposition.split(";"):
                    if "filename=" in part:
                        filename = part.split("=", 1)[1].strip('" ')
                        # Try UTF-8 decoding
                        if filename.startswith("UTF-8''"):
                            filename = urllib.parse.unquote(filename[7:])
                        break

            # Use save_path as directory if it's a directory, otherwise as full path
            if os.path.isdir(save_path):
                save_full_path = os.path.join(save_path, filename or f"document_{document_id}")
            else:
                save_full_path = save_path

            # Write file
            with open(save_full_path, "wb") as f:
                f.write(response.content)

            return save_full_path

    # ============================================================================
    # Auth API
    # ============================================================================

    
    async def list_comment_attachments(self, issue_id: str, comment_id: str):
        """E69: list attachments on an issue comment."""
        data = await self.get(f"/api/issues/{issue_id}/comments/{comment_id}/attachments")
        return data

    async def upload_comment_attachment(self, issue_id: str, comment_id: str, file_path: str):
        """E69: upload a local file onto an issue comment."""
        import httpx
        import os

        url = f"{self.base_url}/api/issues/{issue_id}/comments/{comment_id}/attachments"
        headers = self._get_headers()
        headers.pop("Content-Type", None)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        filename = os.path.basename(file_path)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "application/octet-stream")}
                response = await client.post(url, files=files, headers=headers)
                return self._handle_response(response)

    async def download_comment_attachment(
        self, issue_id: str, comment_id: str, attachment_id: str, out_path: str
    ) -> str:
        """E69: download comment attachment via authenticated /api/attachments/{id}/download."""
        import httpx
        import os
        import urllib.parse

        _ = (issue_id, comment_id)
        url = f"{self.base_url}/api/attachments/{attachment_id}/download"
        headers = self._get_headers()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            if response.status_code >= 400:
                raise APIError(f"Download failed: HTTP {response.status_code}", response.status_code)
            content_disposition = response.headers.get("content-disposition", "")
            filename = None
            if content_disposition and "filename=" in content_disposition:
                for part in content_disposition.split(";"):
                    if "filename=" in part:
                        filename = part.split("=", 1)[1].strip('" ')
                        if filename.startswith("UTF-8''"):
                            filename = urllib.parse.unquote(filename[7:])
                        break
            if os.path.isdir(out_path):
                save_full_path = os.path.join(out_path, filename or f"attachment_{attachment_id}")
            else:
                save_full_path = out_path
            with open(save_full_path, "wb") as f:
                f.write(response.content)
            return save_full_path

    async def create_attachment_signed_url(
        self,
        attachment_id: str,
        *,
        purpose: str = "preview",
        ttl_seconds: int | None = None,
    ) -> dict:
        """E66: mint short-TTL signed URL for an attachment."""
        body: dict = {"purpose": purpose}
        if ttl_seconds is not None:
            body["ttlSeconds"] = ttl_seconds
        data = await self.post(f"/api/attachments/{attachment_id}/signed-url", json=body)
        return data if isinstance(data, dict) else {"raw": data}


    async def login(self, username: str, password: str, _save_to_config: bool = True) -> dict:
        """Login and get JWT token using local authentication.

        Note: Phase 2 后端（sso_enabled=false）使用本地 bcrypt 校验，
        密码以明文提交（不再需要 SSO 加密）。

        Args:
            username: Username
            password: Plaintext password
            _save_to_config: Whether to save credentials to config (default True)

        Returns:
            Login response with token and refreshToken
        """
        result = await self.post("/api/auth/login", data={
            "userName": username,
            "password": password
        })

        # Save credentials and tokens to config if requested
        if _save_to_config and self.config:
            self.config.username = username
            self.config.password = password
            token = result.get("token") or result.get("access_token")
            if token:
                self.config.token = token
                self.token = token
            refresh_token = result.get("refreshToken") or result.get("refresh_token")
            if refresh_token:
                self.config.refresh_token = refresh_token

        return result

    async def refresh(self) -> bool:
        """Use refresh_token to get a new access token.

        读取 config 中保存的 refresh_token，调用 /api/auth/refresh-token；
        成功后更新 config 中的 token 与 refresh_token 并返回 True；
        refresh_token 失效（401）或其他任何异常返回 False。

        Returns:
            True if tokens were refreshed and saved, False otherwise
        """
        if not (self.config and self.config.refresh_token):
            return False

        url = f"{self.base_url}/api/auth/refresh-token"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json={"refreshToken": self.config.refresh_token},
                    headers={"Content-Type": "application/json"}
                )

            if response.status_code != 200:
                logger.warning(f"Refresh token failed: HTTP {response.status_code}")
                return False

            data = response.json()
            # 兼容 {"code": 200, "data": {...}} 包装格式与裸格式
            if data.get("code") is not None and data.get("code") != 200:
                logger.warning(f"Refresh token failed: code={data.get('code')}")
                return False
            payload = data.get("data", data) if isinstance(data, dict) else {}
            token = payload.get("token") or payload.get("access_token")
            if not token:
                return False

            refresh_token = payload.get("refreshToken") or payload.get("refresh_token")

            self.token = token
            self.config.token = token
            if refresh_token:
                self.config.refresh_token = refresh_token
            return True
        except Exception as e:
            logger.warning(f"Refresh token request failed: {e}")
            return False

    async def get_me(self) -> dict:
        """Get current user info."""
        return await self.get("/api/auth/getUserInfo")

    def get_user_id_from_response(self, user_info: dict) -> str | None:
        """Extract user ID from get_me() response.

        Handles multiple response formats:
        - Standard: {"data": {"id": "..."}}
        - Direct: {"id": "..."}
        - Alternative fields: userId, user_id

        Args:
            user_info: Response from get_me()

        Returns:
            User ID as string, or None if not found
        """
        # Try data wrapper first
        data = user_info.get("data") if isinstance(user_info, dict) else user_info
        if isinstance(data, dict):
            user_id = data.get("id") or data.get("userId") or data.get("user_id")
            if user_id:
                return user_id

        # Try direct fields
        if isinstance(user_info, dict):
            return user_info.get("id") or user_info.get("userId") or user_info.get("user_id")

        return None

    async def global_search(self, q: str, limit: int = 10) -> dict:
        """E60: GET /api/search workspace-scoped global search."""
        params = {"q": q, "limit": int(limit)}
        return await self.get("/api/search", params=params)

    async def search_users(self, query: str) -> dict:
        """Search users by name or account.

        Args:
            query: Search keyword for user name or account

        Returns:
            {
                "code": 200,
                "message": "success",
                "data": [
                    {
                        "id": "uuid",
                        "sso_user_id": "sso-id",
                        "sso_account": "account",
                        "sso_name": "Display Name"
                    },
                    ...
                ],
                "timestamp": 1234567890
            }
        """
        return await self.get(f"/api/users/searchable?keyword={query}")

    # ============================================================================
    # Conversation API
    # ============================================================================

    async def list_conversations(self) -> list:
        """List all conversations."""
        data = await self.get("/api/conversations")
        return data if isinstance(data, list) else []

    async def create_conversation(self, title: str = "") -> dict:
        """Create new conversation."""
        return await self.post("/api/conversations", data={"title": title})

    async def send_message(self, conversation_id: str, content: str) -> dict:
        """Send message to conversation."""
        return await self.post(f"/api/conversations/{conversation_id}/message", data={
            "content": content
        })

    async def get_conversation_history(self, conversation_id: str) -> list:
        """Get conversation history."""
        data = await self.get(f"/api/conversations/{conversation_id}/history")
        return data if isinstance(data, list) else []

    # ============================================================================
    # Git API
    # ============================================================================

    async def git_clone(self, repo_url: str, path: str) -> dict:
        """Clone git repository."""
        return await self.post("/api/git/clone", data={
            "url": repo_url,
            "path": path
        })

    async def git_status(self, path: str) -> dict:
        """Get git status."""
        return await self.get("/api/git/status", params={"path": path})

    async def git_commit(self, path: str, message: str) -> dict:
        """Commit changes."""
        return await self.post("/api/git/commit", data={
            "path": path,
            "message": message
        })

    async def git_push(self, path: str) -> dict:
        """Push changes."""
        return await self.post("/api/git/push", data={"path": path})

    # ============================================================================
    # Requirement API
    # ============================================================================

    async def list_requirements(
        self,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        priority: str | None = None,
        project_id: str | None = None,
        assignee_id: str | None = None,
        # Advanced filters
        recent: bool = False,
        updated_today: bool = False,
        unassigned: bool = False
    ) -> dict:
        """List requirements with filtering.

        Args:
            page: Page number (default: 1)
            page_size: Page size (default: 50)
            status: Filter by status
            priority: Filter by priority
            project_id: Filter by project ID
            assignee_id: Filter by assignee ID
            recent: Filter requirements created in last 7 days
            updated_today: Filter requirements updated today
            unassigned: Filter unassigned requirements (assignee_id IS NULL)
        """
        params = {
            "page": page,
            "page_size": page_size
        }
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority
        if project_id:
            params["project_id"] = project_id
        if assignee_id:
            params["assignee_id"] = assignee_id
        if recent:
            params["recent"] = "true"
        if updated_today:
            params["updated_today"] = "true"
        if unassigned:
            params["unassigned"] = "true"

        return await self.get("/api/requirements", params=params)

    async def get_requirement(self, requirement_id: str) -> dict:
        """Get requirement details.

        Automatically detects if requirement_id is:
        - A code (格式: 需求2025-xxx, 需求2026-xxx) -> uses /api/requirements/by-code/{code}
        - A UUID -> uses /api/requirements/{id}

        Args:
            requirement_id: Requirement code (需求2026-112) or UUID

        Returns:
            Requirement details
        """
        import re

        # 检测是否为 code 格式（需求2025-xxx, 需求2026-xxx 等）
        code_pattern = r'^需求\d{4}-\d+$'
        if re.match(code_pattern, requirement_id):
            # 使用 by-code 端点
            return await self.get(f"/api/requirements/by-code/{requirement_id}")
        else:
            # 使用 ID 端点
            return await self.get(f"/api/requirements/{requirement_id}")

    async def create_requirement(
        self,
        title: str,
        description: str = "",
        status: str = "planning",
        priority: str = "medium",
        project_id: str | None = None,
        assignee_id: str | None = None
    ) -> dict:
        """Create a new requirement.

        Automatically converts CLI enum values to API format:
        - priority: lowercase (already lowercase, no conversion needed)
        - status: draft -> DRAFT, active -> CLARIFYING, etc.
        """
        # Normalize enum values to API format
        normalized_priority = _normalize_priority(priority)
        normalized_status = _normalize_requirement_status(status)

        return await self.post("/api/requirements", data={
            "title": title,
            "description": description,
            "status": normalized_status,
            "priority": normalized_priority,
            "project_id": project_id,
            "assignee_id": assignee_id
        })

    async def update_requirement(self, requirement_id: str, **kwargs) -> dict:
        """Update requirement.

        Automatically converts CLI enum values to API format:
        - priority: lowercase (already lowercase, no conversion needed)
        - status: draft -> DRAFT, active -> CLARIFYING, reviewing -> REVIEWING, etc.
        """
        # Normalize enum values to API format
        if "priority" in kwargs and kwargs["priority"]:
            kwargs["priority"] = _normalize_priority(kwargs["priority"])
        if "status" in kwargs and kwargs["status"]:
            kwargs["status"] = _normalize_requirement_status(kwargs["status"])

        return await self.put(f"/api/requirements/{requirement_id}", data=kwargs)

    async def delete_requirement(self, requirement_id: str) -> bool:
        """Delete requirement."""
        await self.delete(f"/api/requirements/{requirement_id}")
        return True

    async def assign_requirement(self, requirement_id: str, assignee_id: str) -> dict:
        """Assign requirement to user."""
        return await self.post(f"/api/requirements/{requirement_id}/assign", data={
            "assignee_id": assignee_id
        })

    async def search_requirements(self, keyword: str, limit: int = 20) -> list:
        """Search requirements by keyword."""
        result = await self.get("/api/requirements/search", params={
            "q": keyword,
            "limit": limit
        })
        return result if isinstance(result, list) else []

    # ============================================================================
    # Issue Collection API
    # ============================================================================

    async def list_collections(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        creator_id: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> dict:
        """List issue collections with filtering."""
        params = {
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        if status:
            params["status"] = status
        if creator_id:
            params["creator_id"] = creator_id
        if search:
            params["search"] = search

        return await self.get("/api/issue-collections", params=params)

    async def get_collection(self, collection_id: str) -> dict:
        """Get issue collection details."""
        return await self.get(f"/api/issue-collections/{collection_id}")

    async def get_collection_statistics(self, collection_id: str) -> dict:
        """Get issue collection statistics."""
        return await self.get(f"/api/issue-collections/{collection_id}/statistics")

    async def create_collection(
        self,
        title: str,
        description: str = "",
        status: str = "draft"
    ) -> dict:
        """Create a new issue collection."""
        return await self.post("/api/issue-collections", data={
            "title": title,
            "description": description,
            "status": status
        })

    async def update_collection(self, collection_id: str, **kwargs) -> dict:
        """Update issue collection."""
        return await self.put(f"/api/issue-collections/{collection_id}", data=kwargs)

    async def delete_collection(self, collection_id: str) -> bool:
        """Delete issue collection."""
        await self.delete(f"/api/issue-collections/{collection_id}")
        return True

    async def parse_collection(
        self,
        collection_id: str,
        issues: list[dict]
    ) -> dict:
        """Parse collection and create issues.

        Args:
            collection_id: Collection ID
            issues: List of issue data dictionaries

        Returns:
            Response with parsed_count and issue_ids
        """
        return await self.post(f"/api/issue-collections/{collection_id}/parse", data={
            "issues": issues
        })

    # ============================================================================
    # 需求评论相关方法
    # ============================================================================

    async def get_requirement_comments(self, requirement_id: str) -> dict:
        """Get requirement comments."""
        return await self.get(f"/api/requirements/{requirement_id}/comments")

    async def add_requirement_comment(
        self,
        requirement_id: str,
        content: str
    ) -> dict:
        """Add comment to requirement."""
        # 使用 FormData 发送
        import httpx

        url = f"{self.base_url}/api/requirements/{requirement_id}/comments"
        headers = self._get_headers()

        # 移除 Content-Type，让 httpx 自动设置 multipart/form-data
        headers.pop("Content-Type", None)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                data={"content": content},
                headers=headers
            )
            return self._handle_response(response)

    async def update_requirement_comment(
        self,
        comment_id: str,
        content: str
    ) -> dict:
        """Update requirement comment."""
        import httpx

        url = f"{self.base_url}/api/comments/{comment_id}"
        headers = self._get_headers()

        # 移除 Content-Type，让 httpx 自动设置 multipart/form-data
        headers.pop("Content-Type", None)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                url,
                data={"content": content},
                headers=headers
            )
            return self._handle_response(response)

    async def delete_requirement_comment(self, comment_id: str) -> dict:
        """Delete requirement comment."""
        return await self.delete(f"/api/comments/{comment_id}")

    # ============================================================================
    # Task Methods
    # ============================================================================

    async def get_task_prompt(self, task_id: str) -> dict:
        """Get task prompt for AI Agent execution.

        Args:
            task_id: Task ID

        Returns:
            Task prompt response with structured Markdown prompt
        """
        return await self.get(f"/api/tasks/{task_id}/prompt")

    async def create_pge_task(self, task_data: dict) -> dict:
        """Create a new PGE task with 3 subtasks.

        Args:
            task_data: Task creation data
                - requirement_id: str
                - title: str
                - description: str (optional)
                - framework: str (default "PGE")
                - required_skills: list[str] (optional)

        Returns:
            Created task response with subtasks
        """
        return await self.post("/api/tasks", data=task_data)

    async def list_tasks(
        self,
        requirement_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0
    ) -> dict:
        """List tasks with optional filtering.

        Args:
            requirement_id: Filter by requirement ID
            status: Filter by status
            limit: Page size (default 20)
            offset: Page offset (default 0)

        Returns:
            Tasks list response
        """
        params = {}
        if requirement_id:
            params["requirement_id"] = requirement_id
        if status:
            params["status"] = status
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        return await self.get("/api/tasks", params=params)

    # ============================================================================
    # Requirement Document API
    # ============================================================================

    async def get_requirement_documents(self, requirement_id: str) -> dict:
        """Get requirement documents.

        Returns:
            Dict with documents list: {"data": [...], "total": N}
        """
        return await self.get(f"/api/requirements/{requirement_id}/documents")

    async def upload_requirement_document(
        self,
        requirement_id: str,
        file_path: str,
        doc_status: str = "DRAFT"
    ) -> dict:
        """Upload document to requirement.

        Args:
            requirement_id: Requirement ID
            file_path: Path to file to upload
            doc_status: Document status (DRAFT, PUBLISHED, ARCHIVED)

        Returns:
            Uploaded document info
        """
        import httpx
        import os

        url = f"{self.base_url}/api/requirements/{requirement_id}/documents"
        headers = self._get_headers()
        # Remove Content-Type to let httpx set multipart/form-data
        headers.pop("Content-Type", None)

        # Check file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get filename from path
        filename = os.path.basename(file_path)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "application/octet-stream")}
                data = {"doc_status": doc_status}

                response = await client.post(
                    url,
                    files=files,
                    data=data,
                    headers=headers
                )
                return self._handle_response(response)

    async def delete_requirement_document(self, requirement_id: str, document_id: str) -> bool:
        """Delete requirement document."""
        await self.delete(f"/api/requirements/{requirement_id}/documents/{document_id}")
        return True

    async def download_requirement_document(self, requirement_id: str, document_id: str, save_path: str) -> str:
        """Download requirement document.

        Args:
            requirement_id: Requirement ID
            document_id: Document ID
            save_path: Path to save the downloaded file

        Returns:
            Path where file was saved
        """
        import httpx
        import os

        url = f"{self.base_url}/api/requirements/{requirement_id}/documents/{document_id}/download"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)

            if response.status_code >= 400:
                raise APIError(f"Download failed: HTTP {response.status_code}", response.status_code)

            # Get filename from Content-Disposition header or use save_path
            content_disposition = response.headers.get("content-disposition", "")
            filename = None

            if content_disposition and "filename=" in content_disposition:
                # Parse filename from header (handles UTF-8 encoding)
                import urllib.parse
                for part in content_disposition.split(";"):
                    if "filename=" in part:
                        filename = part.split("=", 1)[1].strip('" ')
                        # Try UTF-8 decoding
                        if filename.startswith("UTF-8''"):
                            filename = urllib.parse.unquote(filename[7:])
                        break

            # Use save_path as directory if it's a directory, otherwise as full path
            if os.path.isdir(save_path):
                save_full_path = os.path.join(save_path, filename or f"document_{document_id}")
            else:
                save_full_path = save_path

            # Write file
            with open(save_full_path, "wb") as f:
                f.write(response.content)

            return save_full_path
