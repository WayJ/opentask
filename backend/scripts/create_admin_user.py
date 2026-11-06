"""创建（或重置）OpenTask 初始管理员账号。

用途：全新部署的库是空的（``alembic upgrade head`` 只建表，不播种任何账号）。
发布脚本用本文件创建第一个管理员。该用户还没有可用工作区时，再创建一个。
重复执行不重置口令，也不重复成员。

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
from opentask.services.workspace.service import WorkspaceService

# 加载 app 的真实导入图，确保 SQLAlchemy mapper 能解析全部关系。
#
# 为什么不能自己扫 models 包：`opentask/models/__init__.py` 只导出部分模型，
# 其余靠路由模块"顺带"导入（`models/access_token/model.py` 的 AccessToken、
# `models/project_knowledge_base.py` 的 project_knowledge_bases 关联表……）。
# 而**全量扫描反而不行**——仓内有已退役未删除的 `models/datainsight/`（其
# `__init__.py` 仍 import 一个已不存在的 `.report`），导入它会让 mapper 配置
# 报 "expression 'AnalysisReport' failed to locate a name"。
# 应用能跑正是因为它只导入自己需要的那些——所以直接复用应用的导入图最稳。
import opentask.main  # noqa: F401,E402  仅为触发模型注册

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_password() -> str:
    """生成 20 位随机口令（去掉易混淆字符）"""
    alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#%*-_"
    return "".join(secrets.choice(alphabet) for _ in range(20))


async def provision_admin(
    session,
    username: str,
    password: str,
    display_name: str | None = None,
    reset_password: bool = False,
    workspace_name: str = "OpenTask",
    skip_workspace: bool = False,
) -> tuple[int, bool, bool]:
    """在给定会话里准备管理员。

    返回 (退出码, 是否写过口令, 是否新建了工作区)。

    账号已存在且未加 ``--reset-password`` 时不改 ``password_hash``。
    该用户没有可用成员关系时才创建工作区；已有成员不重复插入。
    遗留默认工作区对 ``list_for_user`` 不可见，因此不会被当成已有工作区。
    """
    stats = await seed_user_center(session)

    result = await session.execute(select(UserModel).where(UserModel.username == username))
    user = result.scalar_one_or_none()
    password_applied = False

    if user is not None:
        if reset_password:
            user.password_hash = _pwd_context.hash(password)
            user.status = 1
            user.failed_attempts = 0
            user.locked_until = None
            password_applied = True
            print(f"已重置口令：{username}")
        else:
            print(f"账号已存在，未改口令：{username}（要重置口令加 --reset-password）")
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
        await session.flush()
        password_applied = True
        print(f"已创建管理员：{username}")

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

    workspace_created = False
    if not skip_workspace:
        _ws, workspace_created = await WorkspaceService(session).ensure_owner_workspace(
            owner_user_id=str(user.id),
            name=workspace_name,
        )
        if workspace_created:
            print(f"已创建工作区：{workspace_name}")
        else:
            print(f"已有可用工作区，未新建：{username}")

    await session.commit()
    return 0, password_applied, workspace_created


async def create_admin(
    username: str,
    password: str,
    display_name: str | None = None,
    reset_password: bool = False,
    workspace_name: str = "OpenTask",
    skip_workspace: bool = False,
) -> tuple[int, bool]:
    """返回 (退出码, 是否真的动过口令)。

    第二个返回值很重要：**账号已存在且未加 --reset-password 时不改口令**，
    此时调用方不能把随机生成的口令当作已设置的密码打印出去。
    """
    async with SessionCreator() as session:
        rc, applied, _created = await provision_admin(
            session,
            username,
            password,
            display_name,
            reset_password,
            workspace_name,
            skip_workspace,
        )
    return rc, applied


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
    parser.add_argument(
        "--workspace-name",
        default="OpenTask",
        help="该管理员还没有可用工作区时使用的名称（默认 OpenTask）",
    )
    parser.add_argument(
        "--skip-workspace",
        action="store_true",
        help="不创建工作区（默认会在零个可用成员关系时创建）",
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
        rc, applied = asyncio.run(
            create_admin(
                username,
                password,
                args.name,
                args.reset_password,
                args.workspace_name,
                args.skip_workspace,
            )
        )
    except Exception as exc:  # noqa: BLE001 - 脚本入口需要把异常转成退出码
        print(f"失败：{exc}", file=sys.stderr)
        return 1

    if rc == 0 and generated and applied:
        print(f"口令：{password}（仅此一次，请立即保存）")
    elif rc == 0 and generated and not applied:
        print("（本次未新建账号，生成的口令未生效，原口令保持不变）", file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
