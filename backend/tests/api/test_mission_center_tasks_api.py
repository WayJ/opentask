"""
测试 Mission Center Tasks API

注：/tasks/from-comment 已加 authenticate 依赖（创建者身份取认证用户，
不再信任请求体 created_by）——请求须携带 Bearer token。
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_task_from_comment_requirement(
    test_client: AsyncClient, test_requirement, test_token: str
):
    """测试从需求评论创建任务"""
    response = await test_client.post(
        "/api/mission-center/tasks/from-comment",
        json={
            "source_type": "requirement",
            "source_id": str(test_requirement.id),
            "comment_content": "/task-create 优化性能",
            "description": "优化性能",
            "created_by": "user123"
        },
        headers={"Authorization": f"Bearer {test_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["message"] == "任务创建成功"
    assert data["data"]["title"] == "优化性能"
    assert "REQ-" in data["data"]["description"]
    assert "优化性能" in data["data"]["description"]
    assert data["data"]["link_data"] == [f"requirement:{test_requirement.id}"]
    assert data["data"]["status"] == "pending"


@pytest.mark.asyncio
async def test_create_task_from_comment_issue(
    test_client: AsyncClient, test_session, test_token: str
):
    """测试从 Issue 评论创建任务"""
    from opentask.models.issue.model import Issue
    import uuid
    from datetime import datetime

    # 创建测试 Issue
    issue = Issue(
        id=str(uuid.uuid4()),
        issue_code=f"TEST-ISSUE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}",
        title="测试 Issue",
        description="这是一个测试 Issue",
        type="bug",
        status="open",
        priority="medium",
        reporter_id="test_user",
        created_at=datetime.utcnow()
    )

    test_session.add(issue)
    await test_session.commit()
    await test_session.refresh(issue)

    try:
        response = await test_client.post(
            "/api/mission-center/tasks/from-comment",
            json={
                "source_type": "issue",
                "source_id": str(issue.id),
                "comment_content": "/task-create 修复 Bug",
                "description": "修复 Bug",
                "created_by": "user456"
            },
            headers={"Authorization": f"Bearer {test_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["title"] == "修复 Bug"
        assert "ISSUE" in data["data"]["description"]
        assert data["data"]["link_data"] == [f"issue:{issue.id}"]
    finally:
        await test_session.delete(issue)
        await test_session.commit()


@pytest.mark.asyncio
async def test_create_task_from_comment_invalid_source_type(
    test_client: AsyncClient, test_token: str
):
    """测试使用无效的源类型创建任务"""
    response = await test_client.post(
        "/api/mission-center/tasks/from-comment",
        json={
            "source_type": "invalid_type",
            "source_id": "some-id",
            "comment_content": "/task-create 测试",
            "description": "测试",
            "created_by": "user123"
        },
        headers={"Authorization": f"Bearer {test_token}"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_task_from_comment_source_not_found(
    test_client: AsyncClient, test_token: str
):
    """测试源对象不存在时创建任务"""
    response = await test_client.post(
        "/api/mission-center/tasks/from-comment",
        json={
            "source_type": "requirement",
            "source_id": "non-existent-id",
            "comment_content": "/task-create 测试",
            "description": "测试",
            "created_by": "user123"
        },
        headers={"Authorization": f"Bearer {test_token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_task_from_comment_requires_auth(test_client: AsyncClient):
    """无 token 访问 /tasks/from-comment 被拒（缺 token → 401 / 无效 token → 401）"""
    response = await test_client.post(
        "/api/mission-center/tasks/from-comment",
        json={
            "source_type": "requirement",
            "source_id": "some-id",
            "comment_content": "/task-create 测试",
            "description": "测试",
            "created_by": "user123"
        },
    )
    assert response.status_code == 401

    response = await test_client.post(
        "/api/mission-center/tasks/from-comment",
        json={
            "source_type": "requirement",
            "source_id": "some-id",
            "comment_content": "/task-create 测试",
            "description": "测试",
            "created_by": "user123"
        },
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
