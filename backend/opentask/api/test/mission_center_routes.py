"""
测试端点 - 获取内存中的 Mission Center 任务
用于验证数据，无需认证
"""

from fastapi import APIRouter
from opentask.services.mission_center.service import get_task_service

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/agent-tasks-simple")
async def get_agent_tasks_simple():
    """简单的测试端点"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "rows": [],
            "total": 0
        }
    }


@router.get("/agent-tasks")
async def get_agent_tasks():
    """获取内存中的所有 Agent 任务"""
    service = get_task_service()
    tasks = await service.list_tasks()

    # 转换为字典格式
    result = {
        "code": 200,
        "message": "success",
        "data": {
            "rows": [task.to_dict() for task in tasks],
            "total": len(tasks),
            "current": 1,
            "pageSize": 20,
            "totalPages": 1
        }
    }

    return result


@router.post("/create-sample-tasks")
async def create_sample_tasks():
    """创建示例任务"""
    from opentask.services.mission_center.service import TaskService, TaskPriority

    service = get_task_service()

    tasks = [
        {
            'title': '实现用户登录功能',
            'description': '添加 JWT 认证和登录表单',
            'priority': TaskPriority.HIGH,
            'assignee': 'agent-coding-001'
        },
        {
            'title': '编写 API 文档',
            'description': '使用 Swagger 编写 API 文档',
            'priority': TaskPriority.MEDIUM,
            'assignee': 'agent-coding-002'
        },
        {
            'title': '代码审查',
            'description': '审查代码质量和安全性',
            'priority': TaskPriority.LOW,
            'assignee': 'agent-review-001'
        }
    ]

    created_tasks = []
    for task_data in tasks:
        task = service.create_task(**task_data)
        created_tasks.append(task.to_dict())

    return {
        "code": 200,
        "message": f"成功创建 {len(created_tasks)} 个任务",
        "data": created_tasks
    }


@router.get("/online-agents")
async def get_online_agents():
    """获取在线 Agent 列表"""
    from opentask.services.websocket.hub_service import get_websocket_hub

    hub = get_websocket_hub()
    agents = []

    for agent_id, agent_info in hub.agents.items():
        agents.append({
            "agentId": agent_info["agent_id"],
            "name": agent_info["name"],
            "agentType": agent_info["agent_type"],
            "capabilities": agent_info["capabilities"],
            "status": agent_info["status"],
            "registeredAt": agent_info["registered_at"],
            "lastHeartbeat": agent_info["last_heartbeat"]
        })

    return {
        "code": 200,
        "message": "success",
        "data": {
            "agents": agents,
            "total": len(agents)
        }
    }
