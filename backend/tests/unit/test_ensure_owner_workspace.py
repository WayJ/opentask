"""方案 C：管理员零可用成员关系时才创建工作区。"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.services.workspace.service import DEFAULT_WORKSPACE_ID, WorkspaceService


def _load_admin_script():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "create_admin_user.py"
    spec = importlib.util.spec_from_file_location("create_admin_user_provision", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _user(username: str) -> UserModel:
    return UserModel(
        name=username,
        username=username,
        password_hash="hash-original",
        role="admin",
        status=1,
        token_version=0,
    )


async def _member_count(session, user_id: str) -> int:
    result = await session.execute(
        select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
    )
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_ensure_creates_when_user_has_no_membership(test_session):
    user = _user(f"ws0_{uuid.uuid4().hex[:8]}")
    test_session.add(user)
    await test_session.flush()

    ws, created = await WorkspaceService(test_session).ensure_owner_workspace(
        owner_user_id=str(user.id),
        name="OpenTask",
    )
    assert created is True
    assert ws.name == "OpenTask"
    assert ws.id != DEFAULT_WORKSPACE_ID
    assert await _member_count(test_session, str(user.id)) == 1


@pytest.mark.asyncio
async def test_ensure_does_not_duplicate_existing_member(test_session):
    user = _user(f"ws1_{uuid.uuid4().hex[:8]}")
    test_session.add(user)
    await test_session.flush()
    service = WorkspaceService(test_session)
    first, created = await service.ensure_owner_workspace(owner_user_id=str(user.id), name="OpenTask")
    assert created is True
    second, created_again = await service.ensure_owner_workspace(owner_user_id=str(user.id), name="Other")
    assert created_again is False
    assert second.id == first.id
    assert await _member_count(test_session, str(user.id)) == 1


@pytest.mark.asyncio
async def test_legacy_default_membership_is_not_treated_as_usable(test_session):
    user = _user(f"wsd_{uuid.uuid4().hex[:8]}")
    test_session.add(user)
    await test_session.flush()
    legacy = Workspace(
        id=DEFAULT_WORKSPACE_ID,
        name="Default",
        slug=f"legacy-{uuid.uuid4().hex[:6]}",
        issue_key=f"L{uuid.uuid4().hex[:4]}".upper(),
        created_by=str(user.id),
    )
    test_session.add(legacy)
    await test_session.flush()
    test_session.add(
        WorkspaceMember(workspace_id=DEFAULT_WORKSPACE_ID, user_id=str(user.id), role="owner")
    )
    await test_session.flush()

    ws, created = await WorkspaceService(test_session).ensure_owner_workspace(
        owner_user_id=str(user.id),
        name="OpenTask",
    )
    assert created is True
    assert ws.id != DEFAULT_WORKSPACE_ID
    visible = await WorkspaceService(test_session).list_for_user(str(user.id))
    assert DEFAULT_WORKSPACE_ID not in {row[0].id for row in visible}
    assert ws.id in {row[0].id for row in visible}


@pytest.mark.asyncio
async def test_provision_admin_rerun_does_not_reset_password_or_duplicate(test_session):
    username = f"boot_{uuid.uuid4().hex[:8]}"
    provision_admin = _load_admin_script().provision_admin
    rc, applied, created = await provision_admin(
        test_session,
        username,
        "Passw0rd!",
        reset_password=False,
        workspace_name="OpenTask",
    )
    assert rc == 0
    assert applied is True
    assert created is True

    user = (
        await test_session.execute(select(UserModel).where(UserModel.username == username))
    ).scalar_one()
    original_hash = user.password_hash

    rc2, applied2, created2 = await provision_admin(
        test_session,
        username,
        "OtherPass1",
        reset_password=False,
        workspace_name="OpenTask",
    )
    assert rc2 == 0
    assert applied2 is False
    assert created2 is False
    await test_session.refresh(user)
    assert user.password_hash == original_hash
    assert await _member_count(test_session, str(user.id)) == 1
