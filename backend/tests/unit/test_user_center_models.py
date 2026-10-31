"""user_center 模型注册与建表测试"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from opentask.models.base import DBModel
import opentask.models  # 全量注册


EXPECTED_TABLES = {
    "department", "position", "user_dept", "role", "permission",
    "role_permission", "user_role", "role_dept", "refresh_token",
}


def test_tables_registered():
    missing = EXPECTED_TABLES - set(DBModel.metadata.tables)
    assert not missing, f"缺表: {missing}"


@pytest.mark.asyncio
async def test_create_all_sqlite():
    """新表在 SQLite 可建（禁 MySQL 专属类型）"""
    engine = create_async_engine("sqlite+aiosqlite://")
    tables = [DBModel.metadata.tables[n] for n in EXPECTED_TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))
    await engine.dispose()


def test_user_model_security_fields():
    """user 表安全字段齐备，明文密码指纹字段移除"""
    from opentask.models.user.model import UserModel
    cols = UserModel.__table__.columns
    for f in ("username", "password_hash", "must_change_password", "token_version",
              "dingtalk_user_id", "failed_attempts", "locked_until"):
        assert f in cols, f"缺字段 {f}"
    assert "jwt_token_fingerprint" not in cols


def test_business_tables_have_dept_id():
    """业务表部门归属快照列"""
    tables = ("requirements", "issues", "projects", "knowledge_bases", "documents", "tasks", "agent_tasks")
    for t in tables:
        assert "dept_id" in DBModel.metadata.tables[t].columns, f"{t} 缺 dept_id"
