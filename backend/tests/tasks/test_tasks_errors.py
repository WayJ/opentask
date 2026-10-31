"""契约层错误路径测试（S6 S2：401/403/503 独立语义 + 错误码形状统一）

四类验收用例（sprint 台账 S2）：
- 无凭证 → 401 CONTRACT_AUTH_MISSING
- 错凭证 → 401 CONTRACT_AUTH_INVALID
- 禁操作 → 403 CONTRACT_FORBIDDEN（contract.forbidden_operations 配置禁用）
- 模拟后端不可达 → 503 CONTRACT_UNAVAILABLE（get_session 指向不可达引擎）

另覆盖错误语义优先级与形状统一：
- 401 优先于 403（未认证请求无从谈禁操作）、503 优先于 401
  （依赖不可达时凭证无法验证）；
- 404 CONTRACT_TASK_NOT_FOUND / 422 CONTRACT_STATUS_UNKNOWN 错误码字段；
- GET /capabilities 无 DB 依赖，后端不可达时仍可协商（降级路径）。

错误体统一形状：{"detail": {"code": "CONTRACT_*", "message": "<可读消息>"}}。
401 基础用例另见 test_tasks_auth_capabilities.py（S5），此处为 S6
四类错误路径的自包含套件。
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from opentask.api.tasks.errors import (
    AUTH_CODE_INVALID,
    AUTH_CODE_MISSING,
    CODE_FORBIDDEN,
    CODE_STATUS_UNKNOWN,
    CODE_TASK_NOT_FOUND,
    CODE_UNAVAILABLE,
)
from opentask.api.tasks.mapping import ContractConfigError, get_contract_mapping
from opentask.api.tasks.schemas import CONTRACT_VERSION
from opentask.repositories.base import get_session

from .conftest import TITLE_PREFIX


def _detail(resp) -> dict:
    """取错误体 detail（统一形状 {code, message}）"""
    return resp.json()["detail"]


# ============================================================================
# 模拟后端依赖不可达：get_session 覆盖为指向死端口的引擎
# （127.0.0.1:1 几乎必然连接拒绝；connect timeout=2 兜底防环境静默丢包拖慢用例）
# ============================================================================

DEAD_DB_URL = "postgresql+asyncpg://opentask:opentask@127.0.0.1:1/opentask_test"


@pytest_asyncio.fixture
async def dead_db_client(contract_app) -> AsyncClient:
    """契约 App + get_session 指向不可达数据库（真实 authenticate_contract）"""
    engine = create_async_engine(
        DEAD_DB_URL, poolclass=NullPool, connect_args={"timeout": 2}
    )
    maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autocommit=False
    )

    async def override_get_session():
        session = maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    contract_app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        yield ac
    await engine.dispose()


# ============================================================================
# 一、无凭证 → 401 CONTRACT_AUTH_MISSING
# ============================================================================


@pytest.mark.asyncio
class TestMissingCredentials401:
    async def test_list_without_credentials(self, raw_client):
        resp = await raw_client.get("/tasks")
        assert resp.status_code == 401
        detail = _detail(resp)
        assert detail["code"] == AUTH_CODE_MISSING
        assert detail["message"]  # 可读消息非空
        assert "Bearer" in resp.headers["WWW-Authenticate"]

    async def test_delete_without_credentials(self, raw_client):
        """写端点同样 401（非 403）：契约层缺凭证语义独立"""
        resp = await raw_client.delete(f"/tasks/{uuid.uuid4()}")
        assert resp.status_code == 401
        assert _detail(resp)["code"] == AUTH_CODE_MISSING


# ============================================================================
# 二、错凭证 → 401 CONTRACT_AUTH_INVALID
# ============================================================================


@pytest.mark.asyncio
class TestInvalidCredentials401:
    async def test_bogus_api_key(self, raw_client):
        resp = await raw_client.get(
            "/tasks", headers={"Authorization": "Bearer vk_bogus"}
        )
        assert resp.status_code == 401
        detail = _detail(resp)
        assert detail["code"] == AUTH_CODE_INVALID
        assert detail["message"]

    async def test_garbage_jwt(self, raw_client):
        resp = await raw_client.get(
            "/tasks", headers={"Authorization": "Bearer not-a-jwt"}
        )
        assert resp.status_code == 401
        assert _detail(resp)["code"] == AUTH_CODE_INVALID

    async def test_token_endpoint_wrong_secret(self, raw_client):
        """换 token 端点错凭证：同为 401 INVALID（独立于 403/503）"""
        resp = await raw_client.post(
            "/tasks/token",
            data={"grant_type": "client_credentials", "client_secret": "vk_wrong"},
        )
        assert resp.status_code == 401
        assert _detail(resp)["code"] == AUTH_CODE_INVALID


# ============================================================================
# 三、禁操作 → 403 CONTRACT_FORBIDDEN
# ============================================================================


@pytest.mark.asyncio
class TestForbiddenOperation403:
    async def test_delete_forbidden(self, client, mapping_config):
        """禁 delete_task 后 DELETE → 403，任务本体不受影响"""
        created = await client.post(
            "/tasks", json={"title": f"{TITLE_PREFIX}403删禁用"}
        )
        assert created.status_code == 201, created.text
        task_id = created.json()["id"]

        mapping_config({"contract": {"forbidden_operations": ["delete_task"]}})
        resp = await client.delete(f"/tasks/{task_id}")
        assert resp.status_code == 403
        detail = _detail(resp)
        assert detail["code"] == CODE_FORBIDDEN
        assert "delete_task" in detail["message"]  # 可读消息点明被禁操作

        # 任务本体完好：读取仍 200（仅删除被禁，非整库锁死）
        assert (await client.get(f"/tasks/{task_id}")).status_code == 200

    async def test_create_forbidden(self, client, mapping_config):
        mapping_config({"contract": {"forbidden_operations": ["create_task"]}})
        resp = await client.post(
            "/tasks", json={"title": f"{TITLE_PREFIX}403建禁用"}
        )
        assert resp.status_code == 403
        assert _detail(resp)["code"] == CODE_FORBIDDEN

    async def test_other_operations_unaffected(self, client, mapping_config):
        """只禁 delete 时读写路径照常（最小权限粒度）"""
        mapping_config({"contract": {"forbidden_operations": ["delete_task"]}})
        assert (await client.get("/tasks")).status_code == 200
        assert (
            await client.post("/tasks", json={"title": f"{TITLE_PREFIX}403旁路"})
        ).status_code == 201

    async def test_auth_takes_precedence_over_forbidden(
        self, raw_client, mapping_config
    ):
        """无凭证 + 禁操作：401 优先于 403（鉴权先于禁操作校验）"""
        mapping_config({"contract": {"forbidden_operations": ["delete_task"]}})
        resp = await raw_client.delete(f"/tasks/{uuid.uuid4()}")
        assert resp.status_code == 401
        assert _detail(resp)["code"] == AUTH_CODE_MISSING

    async def test_capabilities_reports_forbidden_operations(
        self, raw_client, mapping_config
    ):
        """能力协商下发禁操作表；未配置时为 none（全放行）"""
        mapping_config(
            {"contract": {"forbidden_operations": ["delete_task", "create_task"]}}
        )
        features = (await raw_client.get("/capabilities")).json()["features"]
        assert features["forbidden_operations"] == "create_task,delete_task"

        mapping_config(None)
        features = (await raw_client.get("/capabilities")).json()["features"]
        assert features["forbidden_operations"] == "none"

    async def test_unknown_operation_in_config_fails_fast(self, mapping_config):
        """配置词表外的操作名 → 快速失败（拒绝静默降级，与 status_mapping 同原则）"""
        mapping_config({"contract": {"forbidden_operations": ["hard_delete"]}})
        with pytest.raises(ContractConfigError, match="hard_delete"):
            get_contract_mapping()


# ============================================================================
# 四、模拟后端不可达 → 503 CONTRACT_UNAVAILABLE
# ============================================================================


@pytest.mark.asyncio
class TestBackendUnavailable503:
    async def test_list_tasks_503(self, dead_db_client):
        resp = await dead_db_client.get("/tasks")
        assert resp.status_code == 503
        detail = _detail(resp)
        assert detail["code"] == CODE_UNAVAILABLE
        assert detail["message"]

    async def test_all_task_endpoints_503(self, dead_db_client):
        """五个 /tasks 端点在依赖不可达时统一 503（不裸抛 500）"""
        task_id = str(uuid.uuid4())
        cases = [
            ("get", "/tasks", {}),
            ("post", "/tasks", {"json": {"title": f"{TITLE_PREFIX}不可达"}}),
            ("get", f"/tasks/{task_id}", {}),
            ("patch", f"/tasks/{task_id}", {"json": {"title": "x"}}),
            ("delete", f"/tasks/{task_id}", {}),
        ]
        for method, path, kwargs in cases:
            resp = await getattr(dead_db_client, method)(path, **kwargs)
            assert resp.status_code == 503, (method, path, resp.status_code)
            assert _detail(resp)["code"] == CODE_UNAVAILABLE

    async def test_token_endpoint_503(self, dead_db_client):
        """换 token 端点同样 503（其凭证校验依赖数据库）"""
        resp = await dead_db_client.post(
            "/tasks/token",
            data={
                "grant_type": "client_credentials",
                "client_secret": "vk_any",
            },
        )
        assert resp.status_code == 503
        assert _detail(resp)["code"] == CODE_UNAVAILABLE

    async def test_503_precedes_401(self, dead_db_client):
        """依赖不可达 + 错凭证：503 优先（凭证无法在依赖不可达时验证）"""
        resp = await dead_db_client.get(
            "/tasks", headers={"Authorization": "Bearer vk_bogus"}
        )
        assert resp.status_code == 503
        assert _detail(resp)["code"] == CODE_UNAVAILABLE

    async def test_capabilities_survives_backend_down(self, dead_db_client):
        """capabilities 无 DB 依赖：后端不可达时仍可协商（消费方降级路径）"""
        resp = await dead_db_client.get("/capabilities")
        assert resp.status_code == 200, resp.text
        assert resp.json()["contract_version"] == CONTRACT_VERSION


# ============================================================================
# 错误码形状统一：404 / 422（契约层语义错误均带 code + message）
# ============================================================================


@pytest.mark.asyncio
class TestCoded404And422:
    async def test_get_task_not_found_coded(self, client):
        resp = await client.get(f"/tasks/{uuid.uuid4()}")
        assert resp.status_code == 404
        detail = _detail(resp)
        assert detail["code"] == CODE_TASK_NOT_FOUND
        assert detail["message"]

    async def test_delete_task_not_found_coded(self, client):
        resp = await client.delete(f"/tasks/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert _detail(resp)["code"] == CODE_TASK_NOT_FOUND

    async def test_query_status_unknown_coded(self, client):
        """查询参数状态词表外 → 422 CONTRACT_STATUS_UNKNOWN（运行时词表校验）"""
        resp = await client.get("/tasks", params={"status": "bogus"})
        assert resp.status_code == 422
        detail = _detail(resp)
        assert detail["code"] == CODE_STATUS_UNKNOWN
        assert detail["message"]

    async def test_create_body_status_unknown_coded(self, client):
        resp = await client.post(
            "/tasks", json={"title": f"{TITLE_PREFIX}422状态", "status": "bogus"}
        )
        assert resp.status_code == 422
        assert _detail(resp)["code"] == CODE_STATUS_UNKNOWN

    async def test_patch_body_status_unknown_coded(self, client):
        created = await client.post(
            "/tasks", json={"title": f"{TITLE_PREFIX}422patch状态"}
        )
        task_id = created.json()["id"]
        resp = await client.patch(
            f"/tasks/{task_id}", json={"status": "bogus"}
        )
        assert resp.status_code == 422
        assert _detail(resp)["code"] == CODE_STATUS_UNKNOWN
