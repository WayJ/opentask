"""token_service 单元测试：签发/轮换/重放/过期/吊销（SQLite 内存库）"""
import hashlib
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import opentask.models  # noqa: F401 全量注册（FK 字符串引用需要）
from opentask.jwt_utils import verify_token
from opentask.models.base import DBModel
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import RefreshToken
from opentask.services.user_center.token_service import TokenService

# FK 解析需要：user（被引用）、refresh_token（本服务）、access_tokens（user 关系引用）
TABLES = ("user", "refresh_token", "access_tokens")


@pytest.fixture
async def session_maker():
    """SQLite 内存库会话工厂"""
    engine = create_async_engine("sqlite+aiosqlite://")
    tables = [DBModel.metadata.tables[n] for n in TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _make_user(session: AsyncSession, username: str = "tester") -> UserModel:
    """建一个最小可用用户"""
    user = UserModel(name=f"用户-{username}", username=username)
    session.add(user)
    await session.commit()
    return user


async def _refresh_rows(session: AsyncSession) -> list[RefreshToken]:
    return list((await session.execute(select(RefreshToken))).scalars().all())


async def test_issue_tokens(session_maker):
    """签发：返回 token 对；库存 sha256 非明文；access 解出 sub/tv"""
    async with session_maker() as session:
        user = await _make_user(session)
        svc = TokenService(session)

        pair = await svc.issue_tokens(user, user_agent="pytest-ua", ip="127.0.0.1")

        assert pair["token"] and pair["refreshToken"]
        assert pair["mustChangePassword"] is False

        # 库中 1 行，存的是哈希不是明文
        rows = await _refresh_rows(session)
        assert len(rows) == 1
        assert rows[0].token_hash == hashlib.sha256(pair["refreshToken"].encode()).hexdigest()
        assert rows[0].token_hash != pair["refreshToken"]
        assert rows[0].user_id == str(user.id)
        assert rows[0].user_agent == "pytest-ua"

        # access claims
        payload = verify_token(pair["token"])
        assert payload["sub"] == str(user.id)
        assert payload["tv"] == user.token_version


async def test_rotate_replay_revokes_all(session_maker):
    """轮换成功；旧 refresh 重放 → 401 且该用户全部 refresh 被吊销"""
    async with session_maker() as session:
        user = await _make_user(session)
        svc = TokenService(session)

        first = await svc.issue_tokens(user)
        # 正常轮换：拿到新对，旧行已吊销
        second = await svc.rotate_refresh(first["refreshToken"])
        assert second["refreshToken"] != first["refreshToken"]
        rows = {r.token_hash: r for r in await _refresh_rows(session)}
        old_row = rows[hashlib.sha256(first["refreshToken"].encode()).hexdigest()]
        assert old_row.revoked_at is not None
        assert old_row.last_used_at is not None

        # 新对可用（轮换返回的 refresh 有效）
        third = await svc.rotate_refresh(second["refreshToken"])
        assert third["refreshToken"] != second["refreshToken"]

        # 重放最早的已吊销 refresh → 401，且该用户全部 refresh 均被吊销
        with pytest.raises(HTTPException) as exc_info:
            await svc.rotate_refresh(first["refreshToken"])
        assert exc_info.value.status_code == 401

        rows = await _refresh_rows(session)
        assert len(rows) == 3
        assert all(r.revoked_at is not None for r in rows)

        # 被全量吊销后，最新 refresh 也不可用
        with pytest.raises(HTTPException) as exc_info2:
            await svc.rotate_refresh(third["refreshToken"])
        assert exc_info2.value.status_code == 401


async def test_rotate_expired(session_maker):
    """过期 refresh → 401"""
    async with session_maker() as session:
        user = await _make_user(session)
        svc = TokenService(session)

        pair = await svc.issue_tokens(user)
        # 把库存行改成已过期
        row = (await _refresh_rows(session))[0]
        row.expires_at = datetime.utcnow() - timedelta(days=1)
        await session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await svc.rotate_refresh(pair["refreshToken"])
        assert exc_info.value.status_code == 401


async def test_rotate_unknown_token(session_maker):
    """不存在的 refresh → 401，且不影响其他用户"""
    async with session_maker() as session:
        user = await _make_user(session)
        svc = TokenService(session)
        await svc.issue_tokens(user)

        with pytest.raises(HTTPException) as exc_info:
            await svc.rotate_refresh("not-a-real-token")
        assert exc_info.value.status_code == 401
        # 未触发全量吊销
        assert all(r.revoked_at is None for r in await _refresh_rows(session))


async def test_rotate_pre_revoked_row(session_maker):
    """直接预置 revoked 行（非本服务轮换产生）→ 401 且触发重放全量吊销

    验证原子条件更新路径：WHERE revoked_at IS NULL 抢不到（rowcount==0），
    回查存在 → 走重放分支，该用户另一条有效 refresh 也被吊销。
    """
    async with session_maker() as session:
        user = await _make_user(session)
        svc = TokenService(session)

        # 一条已被外部吊销（revoked_at 预置）+ 一条仍然有效
        stale_plain = "aa" * 32
        fresh_plain = "bb" * 32
        session.add_all(
            [
                RefreshToken(
                    user_id=str(user.id),
                    token_hash=hashlib.sha256(stale_plain.encode()).hexdigest(),
                    expires_at=datetime.utcnow() + timedelta(days=7),
                    revoked_at=datetime.utcnow() - timedelta(minutes=5),
                ),
                RefreshToken(
                    user_id=str(user.id),
                    token_hash=hashlib.sha256(fresh_plain.encode()).hexdigest(),
                    expires_at=datetime.utcnow() + timedelta(days=7),
                ),
            ]
        )
        await session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await svc.rotate_refresh(stale_plain)
        assert exc_info.value.status_code == 401

        rows = await _refresh_rows(session)
        assert len(rows) == 2
        assert all(r.revoked_at is not None for r in rows)  # 重放触发全量吊销

        # 被连带吊销的 fresh token 也不可用
        with pytest.raises(HTTPException) as exc_info2:
            await svc.rotate_refresh(fresh_plain)
        assert exc_info2.value.status_code == 401


async def test_revoke_counts(session_maker):
    """revoke_refresh / revoke_all 计数正确"""
    async with session_maker() as session:
        user = await _make_user(session)
        svc = TokenService(session)

        p1 = await svc.issue_tokens(user)
        p2 = await svc.issue_tokens(user)

        # 重复吊销同一 token：第一次 True，第二次 False
        assert await svc.revoke_refresh(p1["refreshToken"]) is True
        assert await svc.revoke_refresh(p1["refreshToken"]) is False
        # 不存在的 token
        assert await svc.revoke_refresh("no-such-token") is False

        # 全量吊销：只剩 1 个未吊销
        assert await svc.revoke_all_user_refresh(str(user.id)) == 1
        assert await svc.revoke_all_user_refresh(str(user.id)) == 0  # 再跑为 0


async def test_scope_claim(session_maker):
    """scope=pwd_change 时 access payload 含 scp"""
    async with session_maker() as session:
        user = await _make_user(session)
        svc = TokenService(session)

        pair = await svc.issue_tokens(user, scope="pwd_change")
        payload = verify_token(pair["token"])
        assert payload["scp"] == "pwd_change"

        # 默认无 scp
        pair2 = await svc.issue_tokens(user)
        assert "scp" not in verify_token(pair2["token"])
