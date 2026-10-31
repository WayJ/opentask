"""Agent 管理 API 路由"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.agent_repository import AgentRepository
from opentask.models.agent import Agent
from opentask.repositories.base import get_session

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def list_agents(
    skip: int = Query(0, ge=0, description="分页偏移"),
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    agent_type: Optional[str] = Query(None, description="过滤 Agent 类型"),
    status: Optional[str] = Query(None, description="过滤 Agent 状态"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    session: AsyncSession = Depends(get_session),
):
    """获取 Agent 列表"""
    repo = AgentRepository(session)
    agents = await repo.list(
        skip=skip,
        limit=limit,
        agent_type=agent_type,
        status=status,
        is_active=is_active,
    )

    return {
        "code": 200,
        "message": "success",
        "data": {
            "rows": [
                {
                    "agent_id": agent.agent_id,
                    "agent_type": agent.agent_type,
                    "agent_name": agent.agent_name,
                    "capabilities": agent.capabilities,
                    "model": agent.model,
                    "status": agent.status,
                    "previous_status": agent.previous_status,
                    "connected_at": agent.connected_at.isoformat() if agent.connected_at else None,
                    "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
                    "disconnected_at": agent.disconnected_at.isoformat() if agent.disconnected_at else None,
                    "total_tasks_handled": agent.total_tasks_handled,
                    "successful_tasks": agent.successful_tasks,
                    "failed_tasks": agent.failed_tasks,
                    "total_execution_time": agent.total_execution_time,
                    "current_task_id": agent.current_task_id,
                    "current_task_started_at": agent.current_task_started_at.isoformat() if agent.current_task_started_at else None,
                    "heartbeat_misses": agent.heartbeat_misses,
                    "error_count": agent.error_count,
                    "last_error": agent.last_error,
                    "last_error_at": agent.last_error_at.isoformat() if agent.last_error_at else None,
                    "is_active": agent.is_active,
                    "retired_at": agent.retired_at.isoformat() if agent.retired_at else None,
                    "retired_by": agent.retired_by,
                    "retire_reason": agent.retire_reason,
                    "created_at": agent.created_at.isoformat() if agent.created_at else None,
                    "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
                }
                for agent in agents
            ],
            "total": len(agents),
        },
    }


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
):
    """获取 Agent 详情"""
    repo = AgentRepository(session)
    agent = await repo.get_by_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return {
        "code": 200,
        "message": "success",
        "data": {
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type,
            "agent_name": agent.agent_name,
            "capabilities": agent.capabilities,
            "model": agent.model,
            "status": agent.status,
            "previous_status": agent.previous_status,
            "connected_at": agent.connected_at.isoformat() if agent.connected_at else None,
            "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
            "disconnected_at": agent.disconnected_at.isoformat() if agent.disconnected_at else None,
            "total_tasks_handled": agent.total_tasks_handled,
            "successful_tasks": agent.successful_tasks,
            "failed_tasks": agent.failed_tasks,
            "total_execution_time": agent.total_execution_time,
            "current_task_id": agent.current_task_id,
            "current_task_started_at": agent.current_task_started_at.isoformat() if agent.current_task_started_at else None,
            "heartbeat_misses": agent.heartbeat_misses,
            "error_count": agent.error_count,
            "last_error": agent.last_error,
            "last_error_at": agent.last_error_at.isoformat() if agent.last_error_at else None,
            "is_active": agent.is_active,
            "retired_at": agent.retired_at.isoformat() if agent.retired_at else None,
            "retired_by": agent.retired_by,
            "retire_reason": agent.retire_reason,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
            "metadata": agent.metadata,
        },
    }


@router.post("/{agent_id}/retire")
async def retire_agent(
    agent_id: str,
    retired_by: str = Query(..., description="退役操作者"),
    reason: str = Query(..., description="退役原因"),
    session: AsyncSession = Depends(get_session),
):
    """退役 Agent"""
    repo = AgentRepository(session)

    try:
        agent = await repo.retire(agent_id, retired_by, reason)
        await session.commit()

        return {
            "code": 200,
            "message": f"Agent {agent_id} retired successfully",
            "data": {
                "agent_id": agent.agent_id,
                "status": agent.status,
                "retired_at": agent.retired_at.isoformat() if agent.retired_at else None,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retire agent: {str(e)}")


@router.post("/{agent_id}/reactivate")
async def reactivate_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
):
    """重新激活 Agent"""
    repo = AgentRepository(session)
    agent = await repo.reactivate(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    await session.commit()

    return {
        "code": 200,
        "message": f"Agent {agent_id} reactivated successfully",
        "data": {
            "agent_id": agent.agent_id,
            "is_active": agent.is_active,
        },
    }


@router.get("/stats/summary")
async def get_agent_stats(
    session: AsyncSession = Depends(get_session),
):
    """获取 Agent 统计摘要"""
    repo = AgentRepository(session)

    # 获取所有 Agent
    all_agents = await repo.list(skip=0, limit=1000)

    # 统计数据
    total_agents = len(all_agents)
    online_agents = sum(1 for a in all_agents if a.status in ["online", "idle", "busy"])
    offline_agents = sum(1 for a in all_agents if a.status == "offline")
    retired_agents = sum(1 for a in all_agents if a.status == "retired")
    active_agents = sum(1 for a in all_agents if a.is_active)

    # 任务统计
    total_tasks = sum(a.total_tasks_handled for a in all_agents)
    successful_tasks = sum(a.successful_tasks for a in all_agents)
    failed_tasks = sum(a.failed_tasks for a in all_agents)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "total_agents": total_agents,
            "online_agents": online_agents,
            "offline_agents": offline_agents,
            "retired_agents": retired_agents,
            "active_agents": active_agents,
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": round(successful_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0,
        },
    }
