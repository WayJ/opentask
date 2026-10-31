"""设置（settings）接口测试

原为 dataline 单用户模板的同步 TestClient 用例；现迁移为：
- 独立 SQLite 内存库（每用例全新，保证「无用户/无头像」初始态可测）
- 免认证覆写（源自无鉴权模板；端点本身不消费 current_user）
- 异步 AsyncClient（与 tests/api 其它用例一致的 ASGITransport 模式）
"""
import logging
from base64 import b64encode
from io import BytesIO
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from openai.resources.models import Models as OpenAIModels

from opentask.app import App
from opentask.auth import authenticate
from opentask.models.base import DBModel
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """SQLite 内存库 + 免认证的测试客户端（每用例独立数据库）"""
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    tables = [DBModel.metadata.tables["user"], DBModel.metadata.tables["media"]]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))

    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        """与 repositories.base.get_session 相同的提交/回滚语义"""
        session = maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def override_authenticate():
        """模板用例不带 Authorization 头：覆写认证依赖返回占位用户"""
        return UserModel(name="settings-test", status=1, role="viewer")

    app = App()
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[authenticate] = override_authenticate

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_update_user_info_name(client: AsyncClient) -> None:
    user_in = {"name": "John"}
    response = await client.patch("/api/settings/info", json=user_in)

    assert response.status_code == 200
    assert response.json()["data"] == {
        "name": "John",
        "openai_api_key": None,
        "preferred_openai_model": None,
        "langsmith_api_key": None,
        "openai_base_url": None,
        "sentry_enabled": False,  # 模型 server_default=false()（现行契约；模板时代的默认 True 已改）
        "analytics_enabled": True,
        "hide_sql_preference": False,
    }


@pytest.mark.asyncio
async def test_update_user_info_empty_name(client: AsyncClient) -> None:
    user_in = {"name": ""}
    response = await client.patch("/api/settings/info", json=user_in)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_user_info_long_name(client: AsyncClient) -> None:
    user_in = {"name": "a" * 251}
    response = await client.patch("/api/settings/info", json=user_in)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_user_info_empty_openai_key(client: AsyncClient) -> None:
    user_in = {"openai_api_key": ""}
    response = await client.patch("/api/settings/info", json=user_in)
    assert response.status_code == 422


@pytest.mark.skip(reason="OpenAI key validation is not implemented yet.")
async def test_update_user_info_invalid_openai_key(client: AsyncClient) -> None:
    user_in = {"openai_api_key": "invalid"}
    response = await client.patch("/api/settings/info", json=user_in)
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.skip(reason="OpenAI key is now as SecretStr, check the db for a change instead of using the client")
@patch.object(OpenAIModels, "list")
async def test_update_user_info_valid_openai_key(mock_openai_model_list: MagicMock, client: AsyncClient) -> None:
    mock_model = MagicMock()
    mock_model.id = "gpt-3.5-turbo"
    mock_openai_model_list.return_value = [mock_model]
    openai_key = "sk-Mioanowida"
    user_in = {"openai_api_key": openai_key}
    response = await client.patch("/api/settings/info", json=user_in)
    assert response.status_code == 200, response.json()
    assert response.json()["data"]["openai_api_key"] == openai_key
    mock_openai_model_list.assert_called()


@pytest.mark.asyncio
@patch.object(OpenAIModels, "list")
async def test_update_user_info_extra_fields_ignored(mock_openai_model_list: MagicMock, client: AsyncClient) -> None:
    mock_model = MagicMock()
    mock_model.id = "gpt-3.5-turbo"
    mock_openai_model_list.return_value = [mock_model]
    user_in = {"name": "John", "openai_api_key": "sk-1234", "extra": "extra"}
    response = await client.patch("/api/settings/info", json=user_in)
    assert response.status_code == 200
    assert "extra" not in response.json()["data"]
    mock_openai_model_list.assert_called()


@pytest_asyncio.fixture
@patch.object(OpenAIModels, "list")
async def user_info(mock_openai_model_list: MagicMock, client: AsyncClient) -> dict[str, str]:
    mock_model = MagicMock()
    mock_model.id = "gpt-3.5-turbo"
    mock_openai_model_list.return_value = [mock_model]
    user_in = {
        "name": "John",
        "openai_api_key": "sk-asoiasdfl",
    }
    await client.patch("/api/settings/info", json=user_in)
    return user_in


@pytest.mark.asyncio
@pytest.mark.skip(reason="OpenAI key is now as SecretStr, check the db for a change instead of using the client")
async def test_get_info(client: AsyncClient, user_info: dict[str, str]) -> None:
    # Send a GET request to the /settings/info endpoint
    response = await client.get("/api/settings/info")

    # Check that the response status code is 200
    assert response.status_code == 200

    # Check that the response body contains the expected data
    # Replace this with your actual assertions based on your application's logic
    assert response.json()["data"] == {**user_info, "preferred_openai_model": "gpt-3.5-turbo"}


@pytest.mark.asyncio
async def test_get_info_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/settings/info")
    assert response.status_code == 404


FileTuple = tuple[str, tuple[str, BytesIO, str]]


@pytest.fixture
def avatar_file() -> tuple[FileTuple, bytes]:
    file_data = b"test"
    file_name = "test_file.txt"
    file = ("file", (file_name, BytesIO(file_data), "image/jpeg"))
    return file, file_data


@pytest.mark.asyncio
async def test_upload_avatar(client: AsyncClient, avatar_file: tuple[FileTuple, bytes]) -> None:
    file, file_data = avatar_file
    base64_encoded = b64encode(file_data).decode("utf-8")

    response = await client.post("/api/settings/avatar", files=[file])
    assert response.status_code == 200
    assert response.json()["data"] == {
        "blob": base64_encoded,
    }


@pytest_asyncio.fixture
async def avatar(client: AsyncClient, avatar_file: tuple[FileTuple, bytes]) -> str:
    """Uploads an avatar and returns the base64 encoded blob."""
    file, _ = avatar_file
    response = await client.post("/api/settings/avatar", files=[file])
    return response.json()["data"]["blob"]


@pytest.mark.asyncio
async def test_get_avatar(client: AsyncClient, avatar: str) -> None:
    # Send a GET request to the /settings/avatar endpoint
    response = await client.get("/api/settings/avatar")

    # Check that the response status code is 200
    assert response.status_code == 200

    # Check that the response body contains the expected data
    assert response.json()["data"] == {
        "blob": avatar,
    }


@pytest.mark.asyncio
async def test_get_avatar_no_avatar(client: AsyncClient) -> None:
    response = await client.get("/api/settings/avatar")
    assert response.status_code == 404
