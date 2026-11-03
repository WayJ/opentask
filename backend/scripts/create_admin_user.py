"""创建（或重置）OpenTask 初始管理员账号。

用途：全新部署的库是空的（``alembic upgrade head`` 只建表，不播种任何账号），
而后端**没有注册接口**——只有登录。因此发布后必须显式建出第一个管理员，
否则无人能登录。

用法::

    # 在后端容器内执行（依赖已随镜像装好）
    cd /opt/opentask
    docker compose -f docker-compose.prod.yml exec backend \
        python scripts/create_admin_user.py --username admin --password 'xxx'

    # 不给 --password 时自动生成随机口令并打印（仅打印一次）
    docker compose -f docker-compose.prod.yml exec backend \
        python scripts/create_admin_user.py --username admin

行为：
- **幂等**：账号已存在时默认跳过（不覆盖口令）；加 ``--reset-password`` 才重置。
- 先跑一遍用户中心播种（幂等），确保 ``role`` 表里有 ``admin`` 系统角色；
- 建号后写一行 ``user_role`` 关联，把用户显式挂到 ``admin`` 角色
  （不依赖 ``user.role`` 字符串桥接那条过渡路径）。
- 口令只存 bcrypt 哈希（与 ``AuthService.login_local`` 同一套口径），
  库里没有明文；脚本只在**生成**口令时打印一次。

环境变量：``ADMIN_USERNAME`` / ``ADMIN_PASSWORD`` 可替代同名命令行参数。
"""

from __future__ import annotations

import argparse
import asyncio
import secrets
import sys
from pathlib import Path

# 路径自举：本脚本以 `python scripts/create_admin_user.py` 调用时，sys.path[0] 是
# scripts/ 目录，而 opentask 包在**上一级**（backend/opentask）。镜像里后端依赖是
# `uv sync --no-install-project` 装的——项目自身没有进 venv，故这里必须显式补路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from passlib.context import CryptContext
from sqlalchemy import select

from opentask.models import UserModel
from opentask.models.user_center import Role, UserRole
from opentask.repositories.base import SessionCreator
from opentask.services.user_center.seed import seed_user_center

# UserModel.access_tokens 是字符串式 relationship（"AccessToken"），而
# opentask.models 包**没有导出** AccessToken（只导出了同名的 OAuthAccessToken）。
# 应用侧能跑是因为别的模块先导入了它；本脚本不加载 app，故必须显式导入，
# 否则 mapper 配置期报 "expression 'AccessToken' failed to locate a name"。
from opentask.models.access_token.model import AccessToken  # noqa: F401

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_password() -> str:
    """生成 20 位随机口令（去掉易混淆字符）"""
    alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#%*-_"
    return "".join(secrets.choice(alphabet) for _ in range(20))


async def create_admin(
    username: str,
    password: str,
    display_name: str | None = None,
    reset_password: bool = False,
) -> int:
    """返回 0 成功；非 0 表示失败"""
    async with SessionCreator() as session:
        # 用户中心播种（幂等）：确保 role 表里有 admin 系统角色
        stats = await seed_user_center(session)

        result = await session.execute(select(UserModel).where(UserModel.username == username))
        user = result.scalar_one_or_none()

        if user is not None:
            if not reset_password:
                print(f"账号已存在，未做任何改动：{username}（要重置口令加 --reset-password）")
                return 0
            user.password_hash = _pwd_context.hash(password)
            user.status = 1
            user.failed_attempts = 0
            user.locked_until = None
            print(f"已重置口令：{username}")
        else:
            user = UserModel(
                name=display_name or username,
                username=username,
                password_hash=_pwd_context.hash(password),
                role="admin",
                status=1,
                token_version=0,
            )
            session.add(user)
            await session.flush()  # 生成 user id
            print(f"已创建管理员：{username}")

        # 显式挂到 admin 角色（不依赖 user.role 字符串桥接这条过渡路径）
        role_result = await session.execute(select(Role).where(Role.code == "admin"))
        role = role_result.scalar_one_or_none()
        if role is None:
            print("警告：role 表里没有 admin 系统角色（播种异常），仅依赖 user.role 桥接", file=sys.stderr)
        else:
            link_result = await session.execute(
                select(UserRole).where(
                    UserRole.user_id == str(user.id),
                    UserRole.role_id == str(role.id),
                )
            )
            if link_result.scalar_one_or_none() is None:
                session.add(UserRole(user_id=str(user.id), role_id=str(role.id)))
                await session.flush()
                print(f"已关联角色：admin（权限点 {stats['permissions']} 项）")

        await session.commit()
    return 0


def build_parser() -> argparse.ArgumentParser:
    """命令行契约（抽出来便于单测）"""
    parser = argparse.ArgumentParser(description="创建/重置 OpenTask 初始管理员账号")
    parser.add_argument("--username", default=None, help="登录用户名（默认 admin）")
    parser.add_argument("--password", default=None, help="口令（不给则随机生成并打印）")
    parser.add_argument("--name", default=None, help="显示名（默认同用户名）")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="账号已存在时重置口令（默认只跳过，不覆盖）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    username = args.username or "admin"
    password = args.password
    generated = False
    if not password:
        password = generate_password()
        generated = True

    try:
        rc = asyncio.run(create_admin(username, password, args.name, args.reset_password))
    except Exception as exc:  # noqa: BLE001 - 脚本入口需要把异常转成退出码
        print(f"失败：{exc}", file=sys.stderr)
        return 1

    if rc == 0 and generated:
        print(f"口令：{password}（仅此一次，请立即保存）")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
