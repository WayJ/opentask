"""scope 强制测试（含 F2 库行为回归钉死）

**回归钉死的理由**（防止 python-jose 版本升级静默失守）：

python-jose 3.5.0 在 ``jwt.decode`` **不传** ``audience=`` 时，对带 ``aud`` claim
的 token 直接抛 ``JWTError: Invalid audience``。既有
``opentask.jwt_utils.verify_token`` 正是这种调用，因此带 ``aud`` 的 OAuth access
token 天然进不了全局鉴权链（``/api/*``）与契约层（``/tasks``）。

若将来 python-jose 升级后该行为改变（例如不再校验 aud），OAuth token 就能混入
通用 API 面——只读 scope 形同虚设。因此这里用**测试**把该行为钉死。
"""

import pytest
from httpx import AsyncClient
from jose import jwt

from opentask.jwt_utils import ALGORITHM, SECRET_KEY
from opentask.services.oauth2.client_service import OAuthClientService
from opentask.services.oauth2.token_service import OAuthTokenService

from .conftest import READ_SCOPES, REDIRECT_URI


@pytest.mark.asyncio
async def test_jose_rejects_aud_token_without_audience_parameter():
    """**库行为回归**：带 aud 的 token 在不传 audience= 时必须被拒

    这条测试是整个 scope 强制方案的地基——若它失败，OAuth token 就能混入
    通用 API 面，必须阻断合并。
    """
    from jose.exceptions import JWTError

    token = jwt.encode(
        {"sub": "someone", "aud": "some-client", "scope": "read:tasks"},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    with pytest.raises(JWTError):
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


@pytest.mark.asyncio
async def test_oauth_token_rejected_by_global_api(test_client: AsyncClient, test_session):
    """带 aud 的 OAuth token 进不了通用 API 面（全局鉴权链）→ 401"""
    from opentask.models.user.model import UserModel

    user = UserModel(
        name="scope 用户",
        username="scope_guard_user",
        password_hash=None,
        role="viewer",
        status=1,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)

    client, _secret = await OAuthClientService(test_session).register(
        client_id="scope-guard-client",
        name="范围守卫",
        description=None,
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(user.id),
    )
    pair = await OAuthTokenService(test_session).issue(
        user=user, client_id=client.client_id, scope="read:tasks"
    )

    response = await test_client.get(
        "/api/issues",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    assert response.status_code == 401, (
        f"OAuth token 不应被通用 API 接受，实际 {response.status_code}"
    )


@pytest.mark.asyncio
async def test_oauth_token_rejected_by_contract_tasks(test_client: AsyncClient, test_session):
    """带 aud 的 OAuth token 进不了契约层 /tasks → 401"""
    from opentask.models.user.model import UserModel

    user = UserModel(
        name="契约守卫用户",
        username="contract_guard_user",
        password_hash=None,
        role="viewer",
        status=1,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)

    client, _secret = await OAuthClientService(test_session).register(
        client_id="contract-guard-client",
        name="契约守卫",
        description=None,
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(user.id),
    )
    pair = await OAuthTokenService(test_session).issue(
        user=user, client_id=client.client_id, scope="read:tasks"
    )

    response = await test_client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    assert response.status_code == 401, (
        f"OAuth token 不应被契约层接受，实际 {response.status_code}"
    )


@pytest.mark.asyncio
async def test_session_token_without_aud_still_accepted(test_client: AsyncClient, test_session):
    """防误伤回归：不带 aud 的既有会话 token 仍能正常访问通用 API"""
    from opentask.jwt_utils import create_access_token
    from opentask.models.user.model import UserModel

    user = UserModel(
        name="会话用户",
        username="plain_session_user",
        password_hash=None,
        role="viewer",
        status=1,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)

    token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    response = await test_client.get(
        "/api/issues",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, f"会话 token 应被接受，实际 {response.status_code}"


@pytest.mark.asyncio
async def test_insufficient_scope_returns_403(test_client: AsyncClient, test_session):
    """scope 不足 → 403 insufficient_scope（RFC 6750 §3.1）"""
    from opentask.models.user.model import UserModel

    user = UserModel(
        name="范围不足用户",
        username="insufficient_scope_user",
        password_hash=None,
        role="viewer",
        status=1,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)

    client, _secret = await OAuthClientService(test_session).register(
        client_id="insufficient-scope-client",
        name="范围不足",
        description=None,
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(user.id),
    )
    pair = await OAuthTokenService(test_session).issue(
        user=user, client_id=client.client_id, scope="read:tasks"
    )

    response = await test_client.get(
        "/oauth2/api/projects",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error"] == "insufficient_scope"
    assert "read:projects" in detail["error_description"]


@pytest.mark.asyncio
async def test_read_surface_accepts_authorized_scope(test_client: AsyncClient, test_session):
    """scope 齐备 → 只读数据面放行"""
    from opentask.models.user.model import UserModel

    user = UserModel(
        name="只读放行用户",
        username="read_surface_user",
        password_hash=None,
        role="viewer",
        status=1,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)

    client, _secret = await OAuthClientService(test_session).register(
        client_id="read-surface-client",
        name="只读放行",
        description=None,
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(user.id),
    )
    pair = await OAuthTokenService(test_session).issue(
        user=user, client_id=client.client_id, scope="read:tasks read:projects"
    )

    response = await test_client.get(
        "/oauth2/api/projects",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    assert response.status_code == 200, response.text
    assert "items" in response.json()


@pytest.mark.asyncio
async def test_read_surface_tasks_endpoint_works(test_client: AsyncClient, test_session):
    """只读数据面的任务端点可正常调用（薄封装既有 service 层）

    这条用例覆盖 ``/oauth2/api/tasks`` 的完整路径：状态映射、列表查询、
    标签与用户名批量预取、契约 DTO 转换——只读面与契约层同源不同面，
    任何一环的导入/签名漂移都会在此变红。
    """
    from opentask.models.user.model import UserModel

    user = UserModel(
        name="任务面用户",
        username="read_tasks_user",
        password_hash=None,
        role="viewer",
        status=1,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)

    client, _secret = await OAuthClientService(test_session).register(
        client_id="read-tasks-client",
        name="任务面",
        description=None,
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(user.id),
    )
    pair = await OAuthTokenService(test_session).issue(
        user=user, client_id=client.client_id, scope="read:tasks read:requirements"
    )

    for endpoint in ("/oauth2/api/tasks", "/oauth2/api/requirements"):
        response = await test_client.get(
            endpoint,
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )
        assert response.status_code == 200, f"{endpoint} -> {response.status_code} {response.text}"


@pytest.mark.asyncio
async def test_missing_bearer_token_returns_401(test_client: AsyncClient):
    """缺 Bearer → 401（不是 403）"""
    response = await test_client.get("/oauth2/api/tasks")
    assert response.status_code == 401
