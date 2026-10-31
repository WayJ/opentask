"""
OpenTask 任务管理 API 路由

提供 RESTful API 接口用于任务管理
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from opentask.api.mission_center.comments import router as comments_router
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.user_center.rbac_service import RbacService

from opentask.services.mission_center.service import (
    TaskService,
    TaskPriority,
    TaskStatus,
    get_task_service,
    get_wallet_service,
)
from opentask.schemas.mission_center import (
    TaskCreateRequest,
    TaskResponse,
    TaskUpdateRequest,
    TaskListResponse,
    TaskStatisticsResponse,
    ApiResponse,
    WalletResponse,
    WalletListResponse,
    TransactionResponse,
    TransactionListResponse,
    WalletStatisticsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mission-center", tags=["mission-center"])
router.include_router(comments_router)


class ClaimRequest(BaseModel):
    """Agent 认领任务请求"""
    agent_id: str
    force: bool = False  # 是否强制重新认领


@router.post("/{task_id}/claim", response_model=ApiResponse[TaskResponse])
async def claim_task(task_id: str, claim_request: ClaimRequest):
    """
    Agent 认领任务

    路径参数：
    - task_id: 任务 ID

    请求体：
    - agent_id: Agent ID
    - force: 是否强制重新认领（默认 false）
    """
    service = get_task_service()

    agent_id = claim_request.agent_id
    force = claim_request.force

    # 检查任务是否存在
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 规则 2: 检查 Agent 是否已有活跃任务（单任务限制）
    # 如果是强制重新认领当前任务，跳过此检查
    if not force or task.assignee != agent_id:
        active_task_count = await service.count_active_tasks_for_agent(agent_id)
        if active_task_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Agent 已有 {active_task_count} 个活跃任务，请先完成当前任务后再认领新任务。"
            )

    # 检查任务是否已被认领
    if task.assignee:
        # 如果任务已分配给当前agent，直接返回成功
        if task.assignee == agent_id:
            return ApiResponse(
                code=200,
                message="Task already assigned to this agent",
                data=TaskResponse(**task.to_dict()),
                timestamp=int(datetime.utcnow().timestamp() * 1000),
            )
        # 如果任务被其他agent认领且没有force，拒绝
        if not force:
            raise HTTPException(
                status_code=400,
                detail=f"Task already claimed by {task.assignee}. Use force=true to reclaim."
            )

    # 如果是强制重新认领，记录日志
    if force and task.assignee:
        print(f"[INFO] Force reclaiming task {task_id} from {task.assignee} by {agent_id}")

    # Agent 认领任务
    task = await service.update_task_status(
        task_id=task_id,
        status=TaskStatus.ASSIGNED,
        progress_percentage=0,
        current_step="任务已认领",
        assignee=agent_id
    )

    if not task:
        raise HTTPException(status_code=404, detail="Failed to claim task")

    # 通知 Agent 认领成功
    from opentask.services.websocket.hub_service import get_websocket_hub

    hub = get_websocket_hub()

    claim_message = {
        "id": f"msg_{int(datetime.utcnow().timestamp() * 1000)}",
        "type": "task:claimed",
        "sender": "backend",
        "recipient": agent_id,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {
            "taskId": task.task_id,
            "title": task.title,
            "agentId": agent_id,
            "reclaimed": force and task.assignee != agent_id,
        },
        "version": "1.0"
    }

    await hub.send_to_agent(agent_id, claim_message)
    action = "重新认领" if force else "认领"
    print(f"[OK] Task {task_id} {action} by {agent_id}")

    return ApiResponse(
        code=200,
        message=f"Task {'reclaimed' if force else 'claimed'} successfully",
        data=TaskResponse(**task.to_dict()),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.post("/{task_id}/reclaim", response_model=ApiResponse[TaskResponse])
async def reclaim_task(task_id: str, claim_request: ClaimRequest):
    """
    强制重新认领任务（用于任务失败后重新处理）

    路径参数：
    - task_id: 任务 ID

    请求体：
    - agent_id: Agent ID
    """
    # 设置 force=True 并调用 claim_task
    claim_request.force = True
    return await claim_task(task_id, claim_request)


class ProgressUpdateRequest(BaseModel):
    """任务进度更新请求"""
    agent_id: str
    status: str = "IN_PROGRESS"  # 默认为处理中
    progress_percentage: int = 0  # 0-100
    current_step: str = ""
    message: Optional[str] = None


@router.put("/{task_id}/progress", response_model=ApiResponse[TaskResponse])
async def update_task_progress(
    task_id: str,
    progress_request: ProgressUpdateRequest
):
    """
    更新任务进度（规则1：防止任务超时）

    路径参数：
    - task_id: 任务 ID

    请求体：
    - agent_id: Agent ID
    - status: 任务状态（默认 IN_PROGRESS）
    - progress_percentage: 进度百分比（0-100）
    - current_step: 当前步骤描述
    - message: 进度消息（可选）
    """
    service = get_task_service()

    # 验证进度百分比
    if not 0 <= progress_request.progress_percentage <= 100:
        raise HTTPException(
            status_code=400,
            detail="progress_percentage must be between 0 and 100"
        )

    # 转换状态
    try:
        task_status = TaskStatus(progress_request.status.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {progress_request.status}"
        )

    # 更新任务进度
    task = await service.update_task_status(
        task_id=task_id,
        status=task_status,
        progress_percentage=progress_request.progress_percentage,
        current_step=progress_request.current_step or "处理中",
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    print(f"[PROGRESS] Task {task_id} progress updated: "
          f"{progress_request.progress_percentage}% - {progress_request.current_step}")

    return ApiResponse(
        code=200,
        message="Progress updated successfully",
        data=TaskResponse(**task.to_dict()),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.post("/{task_id}/complete", response_model=ApiResponse[TaskResponse])
async def complete_task(task_id: str, request: dict):
    """
    完成任务并提交结果

    路径参数：
    - task_id: 任务 ID

    请求体：
    - result: 任务结果（JSON 对象）
    - agent_id: Agent ID（可选）
    """
    service = get_task_service()

    agent_id = request.get("agent_id")
    result = request.get("result")

    # 先获取任务信息
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 更新任务状态为完成
    updated_task = await service.update_task_status(
        task_id=task_id,
        status=TaskStatus.COMPLETED,
        progress_percentage=100,
        current_step="任务已完成",
        logs=[
            {
                "type": "completion",
                "result": result,
                "completed_by": agent_id or task.assignee,
                "completed_at": datetime.utcnow().isoformat()
            }
        ]
    )

    if not updated_task:
        raise HTTPException(status_code=404, detail="Failed to complete task")

    print(f"[OK] Task {task_id} completed by {agent_id or task.assignee}")

    return ApiResponse(
        code=200,
        message="Task completed successfully",
        data=TaskResponse(**updated_task.to_dict()),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.post("", response_model=ApiResponse[TaskResponse])
async def create_task(
    request: TaskCreateRequest,
    current_user: UserModel = Depends(authenticate),
    db: AsyncSession = Depends(get_session),
):
    """
    创建新任务

    请求体：
    - title: 任务标题
    - description: 任务描述
    - priority: 优先级 (low/medium/high/urgent)
    - assignee: 分配给谁
    - deadline: 截止时间（可选）
    - metadata: 元数据（可选）
    - requirements: 需求列表（可选）
    """
    service = get_task_service()

    # 转换优先级
    try:
        priority = TaskPriority(request.priority)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid priority value")

    # 部门归属快照：取创建人主部门写入（无归属则保持 NULL）
    dept_id = await RbacService(db).get_primary_dept_id(current_user)

    task = await service.create_task(
        title=request.title,
        description=request.description,
        priority=priority,
        assignee=request.assignee,
        deadline=request.deadline,
        metadata=request.metadata,
        requirements=request.requirements,
        acceptance_criteria=request.acceptance_criteria,
        reward=request.reward,
        dept_id=dept_id,
    )

    # 通过 WebSocket Hub 发送任务给 Agent
    from opentask.services.websocket.hub_service import get_websocket_hub
    import json
    from datetime import datetime

    hub = get_websocket_hub()

    # 构造任务提交消息
    task_message = {
        "id": f"msg_{int(datetime.utcnow().timestamp() * 1000)}",
        "type": "task:submit",
        "sender": "backend",
        "recipient": "broadcast",
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {
            "taskId": task.task_id,
            "title": task.title,
            "description": task.description or "",
            "priority": str(task.priority).upper(),
            "deadline": task.deadline,
        },
        "version": "1.0"
    }

    # 任务分发逻辑
    if task.assignee:
        # 如果指定了 Agent，直接发送给该 Agent
        success = await hub.send_to_agent(task.assignee, task_message)
        if success:
            print(f"[OK] Task sent to agent: {task.assignee}")
        else:
            print(f"[WARN] Agent not found: {task.assignee}")
    else:
        # 如果没有指定 Agent，广播给所有在线 Agent，让它们主动认领
        # 临时方案：使用 broadcast 方法，它会发送给 frontend 和 backend
        # 实际的 Agent 认领流程会在后续版本中完善
        await hub.broadcast(task_message, targets={"frontend", "backend"})
        print(f"[OK] Task broadcasted for claiming")

    return ApiResponse(
        code=200,
        message="success",
        data=TaskResponse(**task.to_dict()),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.get("", response_model=ApiResponse[TaskListResponse])
async def list_tasks(
    status: Optional[str] = Query(None, description="按状态过滤"),
    assignee: Optional[str] = Query(None, description="按分配对象过滤"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: UserModel = Depends(authenticate),
    db: AsyncSession = Depends(get_session),
):
    """
    列出任务

    查询参数：
    - status: 任务状态过滤
    - assignee: 分配对象过滤
    - limit: 每页数量（默认 20）
    - offset: 偏移量（默认 0）

    数据范围过滤：仅按部门可见集（ALL 档零过滤）。
    """
    service = get_task_service()

    # 数据范围：ALL → None（零过滤）；SELF → 空集（结果恒空）
    visible_dept_ids = await RbacService(db).get_visible_dept_ids(current_user)

    # 转换状态
    task_status = None
    if status:
        try:
            task_status = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")

    tasks = await service.list_tasks(
        status=task_status, assignee=assignee, limit=limit, offset=offset,
        visible_dept_ids=visible_dept_ids,
    )

    # 获取总数（使用更大的limit来模拟count）
    all_tasks = await service.list_tasks(
        status=task_status, assignee=assignee, limit=10000, offset=0,
        visible_dept_ids=visible_dept_ids,
    )
    total = len(all_tasks)

    return ApiResponse(
        code=200,
        message="success",
        data=TaskListResponse(
            rows=[TaskResponse(**t.to_dict()) for t in tasks],
            total=total,
            current=offset // limit + 1,
            pageSize=limit,
            totalPages=(total + limit - 1) // limit,
        ),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


# ========== 💰 钱包相关 API (必须在 /{task_id} 之前) ==========

@router.get("/wallets", response_model=ApiResponse[WalletListResponse])
async def get_all_wallets():
    """
    获取所有钱包列表

    返回：
    - wallets: 钱包列表
    - total_balance: 所有钱包总余额
    - total_agents: Agent 总数
    """
    wallet_service = get_wallet_service()
    wallets = await wallet_service.get_all_wallets()

    wallet_responses = [WalletResponse(**w.to_dict()) for w in wallets]

    return ApiResponse(
        code=200,
        message="success",
        data=WalletListResponse(
            wallets=wallet_responses,
            total_balance=sum(w.balance for w in wallets),
            total_agents=len(wallets),
        ),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.get("/wallets/stats/summary", response_model=ApiResponse[WalletStatisticsResponse])
async def get_wallet_stats():
    """
    获取钱包统计信息

    返回：
    - total_balance: 所有钱包总余额
    - total_earned: 所有钱包累计获得
    - total_spent: 所有钱包累计消费
    - transaction_count: 交易总数
    - active_wallets: 活跃钱包数（余额 > 0）
    """
    wallet_service = get_wallet_service()
    stats = await wallet_service.get_statistics()

    return ApiResponse(
        code=200,
        message="success",
        data=WalletStatisticsResponse(**stats),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.get("/transactions", response_model=ApiResponse[TransactionListResponse])
async def get_all_transactions(
    agent_id: Optional[str] = Query(None, description="筛选指定 Agent 的交易"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    获取交易流水列表

    查询参数：
    - agent_id: 可选，筛选指定 Agent 的交易
    - limit: 每页数量（默认 20）
    - offset: 偏移量（默认 0）

    返回：
    - transactions: 交易列表
    - total: 总数
    - current: 当前页
    - pageSize: 每页数量
    - totalPages: 总页数
    """
    wallet_service = get_wallet_service()
    transactions, total = await wallet_service.get_transactions(
        agent_id=agent_id, limit=limit, offset=offset
    )

    transaction_responses = [TransactionResponse(**t.to_dict()) for t in transactions]

    current = offset // limit + 1 if limit > 0 else 1
    total_pages = (total + limit - 1) // limit if limit > 0 else 1

    return ApiResponse(
        code=200,
        message="success",
        data=TransactionListResponse(
            transactions=transaction_responses,
            total=total,
            current=current,
            pageSize=limit,
            totalPages=total_pages,
        ),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.get("/health", response_model=ApiResponse[dict])
async def get_health_status():
    """
    获取任务系统健康状态

    返回：
    - stale_tasks: 超时任务数量
    - active_agents: 活跃 Agent 数量
    - monitor_service: 监控服务状态
    """
    service = get_task_service()

    # 获取超时任务数量（1小时）
    stale_tasks = await service.get_stale_tasks(timeout_hours=1)

    # 统计活跃任务数量（用来估算活跃 Agent）
    from opentask.repositories.mission_center_repository import AgentTaskRepository
    from opentask.repositories.base import SessionCreator

    async with SessionCreator() as session:
        repo = AgentTaskRepository()
        active_tasks = await repo.list_tasks(
            session=session,
            status="in_progress",
            limit=1000,
            offset=0
        )

        # 统计唯一 Agent
        unique_agents = set(task.assignee for task in active_tasks if task.assignee)

    return ApiResponse(
        code=200,
        message="success",
        data={
            "stale_tasks": len(stale_tasks),
            "active_agents": len(unique_agents),
            "active_tasks": len(active_tasks),
            "monitor_service": "running",
            "timestamp": datetime.utcnow().isoformat()
        },
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.get("/{task_id}", response_model=ApiResponse[TaskResponse])
async def get_task(task_id: str):
    """
    获取任务详情

    路径参数：
    - task_id: 任务 ID
    """
    service = get_task_service()
    task = await service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return ApiResponse(
        code=200,
        message="success",
        data=TaskResponse(**task.to_dict()),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.get("/wallets/{agent_id}", response_model=ApiResponse[WalletResponse])
async def get_agent_wallet(agent_id: str):
    """
    获取指定 Agent 的钱包

    路径参数：
    - agent_id: Agent ID

    返回：
    - 钱包信息
    """
    wallet_service = get_wallet_service()
    wallet = await wallet_service.get_wallet(agent_id)

    if not wallet:
        # 如果钱包不存在，自动创建
        wallet = await wallet_service.get_or_create_wallet(agent_id)

    return ApiResponse(
        code=200,
        message="success",
        data=WalletResponse(**wallet.to_dict()),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.patch("/{task_id}", response_model=ApiResponse[TaskResponse])
async def update_task(task_id: str, request: TaskUpdateRequest):
    """
    更新任务状态

    路径参数：
    - task_id: 任务 ID

    请求体：
    - status: 新状态
    - progress_percentage: 进度百分比
    - current_step: 当前步骤
    """
    service = get_task_service()

    # 转换状态
    task_status = None
    if request.status:
        try:
            task_status = TaskStatus(request.status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")

    # 💰 检查任务是否完成，如果是则添加金币奖励
    if task_status == TaskStatus.COMPLETED:
        # 先获取任务信息
        existing_task = await service.get_task(task_id)
        if existing_task and existing_task.assignee and existing_task.reward:
            # 添加金币奖励到 Agent 钱包
            wallet_service = get_wallet_service()
            await wallet_service.add_transaction(
                agent_id=existing_task.assignee,
                amount=existing_task.reward,
                transaction_type="task_reward",
                description=f"完成任务: {existing_task.title}",
                related_task_id=task_id,
            )

    task = await service.update_task_status(
        task_id=task_id,
        status=task_status or TaskStatus.IN_PROGRESS,
        progress_percentage=request.progress_percentage or 0,
        current_step=request.current_step or "",
        logs=request.logs,
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return ApiResponse(
        code=200,
        message="success",
        data=TaskResponse(**task.to_dict()),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.post("/{task_id}/cancel", response_model=ApiResponse[TaskResponse])
async def cancel_task(task_id: str, reason: str = ""):
    """
    取消任务

    路径参数：
    - task_id: 任务 ID

    请求体：
    - reason: 取消原因
    """
    service = get_task_service()
    task = await service.cancel_task(task_id, reason)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return ApiResponse(
        code=200,
        message="Task cancelled successfully",
        data=TaskResponse(**task.to_dict()),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.delete("/{task_id}", response_model=ApiResponse[None])
async def delete_task(task_id: str):
    """
    删除任务

    路径参数：
    - task_id: 任务 ID
    """
    service = get_task_service()
    success = await service.delete_task(task_id)

    if not success:
        raise HTTPException(status_code=404, detail="Task not found")

    return ApiResponse(
        code=200,
        message="Task deleted successfully",
        data=None,
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


@router.get("/stats/summary", response_model=ApiResponse[TaskStatisticsResponse])
async def get_statistics():
    """
    获取任务统计信息

    返回：
    - total: 总任务数
    - by_status: 按状态分组统计
    - by_priority: 按优先级分组统计
    """
    service = get_task_service()
    stats = await service.get_statistics()

    return ApiResponse(
        code=200,
        message="success",
        data=TaskStatisticsResponse(**stats),
        timestamp=int(datetime.utcnow().timestamp() * 1000),
    )


# 健康检查端点已移动到文件前面，以避免被 /{task_id} 路由拦截


# ========== 📝 从评论创建任务相关 API ==========

class CreateTaskFromCommentRequest(BaseModel):
    """从评论创建任务请求"""
    source_type: str  # "requirement" | "issue"
    source_id: str
    comment_content: str
    description: str
    created_by: str


@router.post("/tasks/from-comment", response_model=ApiResponse[TaskResponse])
async def create_task_from_comment(
    request: CreateTaskFromCommentRequest,
    current_user: UserModel = Depends(authenticate),
    db: AsyncSession = Depends(get_session),
):
    """从评论创建任务

    请求体：
    - source_type: 源类型 ("requirement" | "issue")
    - source_id: 源对象 ID
    - comment_content: 评论内容
    - description: 用户描述的任务标题
    - created_by: 创建者 ID（已废弃：一律取认证用户真实身份，不再信任请求体）
    """
    service = get_task_service()

    # 验证源类型
    if request.source_type not in ["requirement", "issue"]:
        raise HTTPException(status_code=400, detail=f"不支持的源类型: {request.source_type}")

    # 创建者身份取认证用户，防止请求体伪造他人 ID
    created_by = str(current_user.id)

    # 部门归属快照：取创建人主部门写入（无归属则保持 NULL）
    dept_id = await RbacService(db).get_primary_dept_id(current_user)

    # 获取源对象上下文
    try:
        context = await service.get_source_context(request.source_type, request.source_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 构建完整描述
    full_description = service.build_task_description(
        context,
        request.comment_content,
        request.description
    )

    # 构建 link_data
    link_data = [f"{request.source_type}:{request.source_id}"]

    # 创建任务
    try:
        task = await service.create_task_with_links(
            title=request.description,
            description=full_description,
            link_data=link_data,
            context={
                **context,
                "comment_content": request.comment_content,
                "created_by": created_by
            },
            created_by=created_by,
            dept_id=dept_id,
        )

        return ApiResponse(
            code=200,
            message="任务创建成功",
            data=TaskResponse(**task.to_dict()),
            timestamp=int(datetime.utcnow().timestamp() * 1000)
        )
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="任务创建失败，请重试")
