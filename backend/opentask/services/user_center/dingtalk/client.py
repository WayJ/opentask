"""钉钉开放平台 API 封装（企业内部应用，旧版服务端 topapi）

文档：https://open.dingtalk.com/document/

设计约定：
- 接口窄、可 mock：同步对账（sync_service）与免登（auth）只依赖本文件的
  5 个方法，测试用 FakeDingTalkClient 注入即可，不发真实请求；
- 未配置 app_key/app_secret 时构造即 raise DingTalkError（同步接口
  禁止空凭据调用，路由层据此返回 400）；
- 所有方法失败统一 raise DingTalkError（含 errmsg），上层捕获后转
  HTTPException，不透传钉钉原始响应结构。
"""
import time
from typing import Any

import httpx

from opentask.config import config

# access token 提前刷新余量（秒），避免临界过期
_TOKEN_REFRESH_MARGIN = 60

# user/list 游标分页页数上限（每页 100 条，1000 页 = 10 万用户，超限视为分页异常）
_MAX_LIST_PAGES = 1000


class DingTalkError(Exception):
    """钉钉 API 调用失败（配置缺失 / 网络 / errcode != 0）"""


class DingTalkClient:
    """钉钉开放平台客户端（企业内部应用）

    方法返回的数据结构（dict 字段取自钉钉 v2 topapi 响应的 result）：
    - list_sub_depts(parent_id) -> [{"dept_id": int, "name": str, "parent_id": int, ...}]
    - list_dept_users(dept_id)  -> [{"userid": str, "name": str, ...}]（内部游标分页循环）
    - get_user_detail(userid)   -> {"userid": str, "name": str,
                                    "dept_id_list": [int, ...], "main_dept_id"?: int, ...}
    - get_userid_by_code(code)  -> userid（免登用）
    """

    BASE = "https://oapi.dingtalk.com"

    def __init__(self, app_key: str | None = None, app_secret: str | None = None):
        key = app_key or config.dingtalk_app_key
        secret = app_secret or config.dingtalk_app_secret
        if not key or not secret:
            raise DingTalkError(
                "未配置钉钉应用凭据（DINGTALK_APP_KEY / DINGTALK_APP_SECRET）"
            )
        self.app_key = key
        self.app_secret = secret
        # gettoken 结果缓存（钉钉 token 有效期 7200s）
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    # ---- 内部工具 ----

    async def _token(self) -> str:
        """获取企业 access token，缓存至过期前 60s"""
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.get(
                    f"{self.BASE}/gettoken",
                    params={"appkey": self.app_key, "appsecret": self.app_secret},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise DingTalkError(f"钉钉 gettoken 请求失败: {e}") from e
        if data.get("errcode") != 0:
            raise DingTalkError(
                f"钉钉 gettoken 失败: {data.get('errmsg', 'unknown error')}"
            )
        expires_in = int(data.get("expires_in", 7200))
        self._access_token = data["access_token"]
        self._token_expires_at = time.monotonic() + max(expires_in - _TOKEN_REFRESH_MARGIN, 0)
        return self._access_token

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST topapi（access_token 走 query 参数，业务参数走 JSON body）。

        errcode != 0 时 raise DingTalkError（含 errmsg），成功返回 result 字段。
        """
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.post(
                    f"{self.BASE}{path}",
                    params={"access_token": await self._token()},
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise DingTalkError(f"钉钉 {path} 请求失败: {e}") from e
        if data.get("errcode") != 0:
            raise DingTalkError(
                f"钉钉 {path} 失败: {data.get('errmsg', 'unknown error')}"
            )
        return data.get("result") or {}

    # ---- 通讯录 ----

    async def list_sub_depts(self, parent_id: int) -> list[dict]:
        """列出某部门的直接子部门（topapi/v2/department/listsub）"""
        result = await self._post(
            "/topapi/v2/department/listsub", {"dept_id": parent_id}
        )
        # listsub 的 result 直接是数组（user/list 的 result 才是 dict）
        if isinstance(result, list):
            return result
        return result.get("result") or []

    async def list_dept_users(self, dept_id: int) -> list[dict]:
        """列出部门全部用户（topapi/v2/user/list，游标分页循环）。

        防御：next_cursor 与上一轮相同（钉钉数据/接口异常）或页数超上限
        _MAX_LIST_PAGES 时抛 DingTalkError，避免死循环。
        """
        users: list[dict] = []
        cursor = 0
        pages = 0
        while True:
            result = await self._post(
                "/topapi/v2/user/list",
                {"dept_id": dept_id, "cursor": cursor, "size": 100},
            )
            users.extend(result.get("list") or [])
            pages += 1
            if not result.get("has_more"):
                return users
            next_cursor = int(result.get("next_cursor", 0))
            if next_cursor == cursor or pages >= _MAX_LIST_PAGES:
                raise DingTalkError(
                    f"钉钉 user/list 分页异常（dept_id={dept_id}，"
                    f"第 {pages} 页 next_cursor={next_cursor} 停滞或超页数上限）"
                )
            cursor = next_cursor

    async def get_user_detail(self, userid: str) -> dict:
        """用户详情（topapi/v2/user/get）：name / dept_id_list / 主部门等"""
        return await self._post("/topapi/v2/user/get", {"userid": userid})

    # ---- 免登（Task 3 复用） ----

    async def get_userid_by_code(self, auth_code: str) -> str:
        """免登码换 userid（topapi/v2/user/getuserinfo）"""
        result = await self._post(
            "/topapi/v2/user/getuserinfo", {"code": auth_code}
        )
        userid = result.get("userid")
        if not userid:
            raise DingTalkError("钉钉免登失败: 响应缺少 userid")
        return userid
