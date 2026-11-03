"""
SSO 平台客户端服务

负责与 SSO 平台交互，包括用户信息获取等
"""
import logging
from typing import Optional

import httpx
from fastapi import HTTPException

from opentask.config import config
from opentask.services.sso_protocol import UPSTREAM_CLIENT_HEADER, UPSTREAM_CURRENT_USER_PATH
from opentask.models.user.schema import SsoUserInfo

logger = logging.getLogger(__name__)


class SsoClient:
    """SSO 平台客户端"""

    def __init__(self):
        self.base_url = config.sso_base_url
        self.app_code = config.sso_app_code
        self.timeout = config.sso_timeout

    async def get_current_user(self, token: str) -> SsoUserInfo:
        """
        获取当前登录用户信息

        Args:
            token: SSO 认证 token

        Returns:
            SsoUserInfo: SSO 用户信息

        Raises:
            HTTPException: token 无效或请求失败
        """
        url = f"{self.base_url}{UPSTREAM_CURRENT_USER_PATH}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": token,
                        "App-Code": self.app_code,
                        UPSTREAM_CLIENT_HEADER: "pc",
                        "Vue-Version": "3"
                    },
                    # params={
                    #     # "systemCode": "ACCS",
                    #     "isBackend": "0"
                    # }
                )
                response.raise_for_status()
                data = response.json()

                # 检查 SSO 响应码
                if data.get("code") != 200:
                    logger.warning(f"SSO token 验证失败: {data.get('msg', 'Unknown error')}")
                    raise HTTPException(status_code=401, detail="SSO token无效或已过期")

                # 提取 userInfo 部分
                user_data = data.get("data", {}).get("userInfo")
                if not user_data:
                    logger.error("SSO 响应缺少 userInfo 数据")
                    raise HTTPException(status_code=500, detail="SSO API返回数据格式错误")

                logger.info(f"成功获取 SSO 用户信息: {user_data.get('userAccount')}")

                return SsoUserInfo(
                    userId=user_data.get("userId"),
                    userAccount=user_data.get("userAccount"),
                    userName=user_data.get("userName"),
                    headIcon=user_data.get("headIcon"),
                    organizeId=user_data.get("organizeId"),
                    organizeName=user_data.get("organizeName"),
                    positionId=user_data.get("positionId"),
                    positionName=user_data.get("positionName"),
                )

        except httpx.TimeoutException:
            logger.error(f"SSO API 请求超时: {url}")
            raise HTTPException(status_code=504, detail="SSO 服务超时，请稍后重试")
        except httpx.HTTPStatusError as e:
            logger.error(f"SSO API HTTP 错误: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=502, detail=f"SSO 服务错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"SSO API 请求失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"SSO 服务不可用: {str(e)}")


# 全局单例
sso_client = SsoClient()
