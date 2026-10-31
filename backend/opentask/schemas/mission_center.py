"""
任务管理 API 的数据模型和 Schema
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Generic, TypeVar, Union
from datetime import datetime

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    code: int
    message: str
    data: Optional[T] = None
    timestamp: int


class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    title: str = Field(..., description="任务标题", min_length=1, max_length=200)
    description: str = Field(..., description="任务描述")
    priority: str = Field(..., description="优先级: low/medium/high/urgent")
    assignee: Optional[str] = Field(None, description="分配给谁（可选，不填则由 Agent 主动认领）")
    deadline: Optional[str] = Field(None, description="截止时间 (ISO 8601)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    requirements: Optional[List[str]] = Field(None, description="需求列表")
    # 🎯 新增字段
    acceptance_criteria: Optional[List[str]] = Field(None, description="验收标准 - 明确任务完成的判断条件")
    reward: Optional[int] = Field(None, description="金币奖励 - 给 Agent 的动力")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    title: str
    description: str
    priority: str
    assignee: Optional[str]
    deadline: Optional[str]
    metadata: Dict[str, Any]
    requirements: List[str]
    # 🎯 新增字段
    acceptance_criteria: Optional[List[str]] = None
    reward: Optional[int] = None
    status: str
    progress_percentage: int
    current_step: str
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[Dict[str, Any]]
    logs: Optional[List[Dict[str, Any]]] = None
    execution_time_ms: Optional[int]
    progressHistory: List[Dict[str, Any]] = []  # 🔥 进度历史记录

    @field_validator('logs', mode='before')
    @classmethod
    def normalize_logs(cls, v):
        """规范化 logs 字段 - 向后兼容旧数据"""
        if v is None:
            return None

        # 如果是字典（旧格式），转换为列表
        if isinstance(v, dict):
            return [v]

        # 如果是列表但包含字符串（旧格式），转换
        if isinstance(v, list):
            # 如果第一个元素是字符串，说明是旧格式 ['result', 'completed_by', ...]
            # 这种情况下返回空列表，因为数据已经损坏
            if v and isinstance(v[0], str):
                return []

        return v


class TaskUpdateRequest(BaseModel):
    """更新任务请求"""
    status: Optional[str] = Field(None, description="新状态")
    progress_percentage: Optional[int] = Field(None, ge=0, le=100, description="进度百分比")
    current_step: Optional[str] = Field(None, description="当前步骤")
    logs: Optional[List[Dict[str, str]]] = Field(None, description="日志列表")


class TaskListResponse(BaseModel):
    """任务列表响应"""
    rows: List[TaskResponse]
    total: int
    current: int
    pageSize: int
    totalPages: int


class TaskStatisticsResponse(BaseModel):
    """任务统计响应"""
    total: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]


# ========== 💰 钱包相关 Schemas ==========

class WalletResponse(BaseModel):
    """钱包响应"""
    agent_id: str
    balance: int = Field(..., description="当前余额（金币）")
    total_earned: int = Field(..., description="累计获得金币")
    total_spent: int = Field(..., description="累计消费金币")
    created_at: str
    updated_at: str


class WalletListResponse(BaseModel):
    """钱包列表响应"""
    wallets: List[WalletResponse]
    total_balance: int = Field(..., description="所有钱包总余额")
    total_agents: int


class TransactionCreateRequest(BaseModel):
    """创建交易请求（内部使用）"""
    agent_id: str
    amount: int = Field(..., description="交易金额（正数为收入，负数为支出）")
    transaction_type: str = Field(..., description="交易类型: task_reward, task_penalty, system_adjustment")
    description: str = Field(..., description="交易描述")
    related_task_id: Optional[str] = Field(None, description="关联任务ID")


class TransactionResponse(BaseModel):
    """交易响应"""
    id: str
    agent_id: str
    amount: int
    balance_after: int = Field(..., description="交易后余额")
    transaction_type: str
    description: str
    related_task_id: Optional[str]
    created_at: str


class TransactionListResponse(BaseModel):
    """交易列表响应"""
    transactions: List[TransactionResponse]
    total: int
    current: int
    pageSize: int
    totalPages: int


class WalletStatisticsResponse(BaseModel):
    """钱包统计响应"""
    total_balance: int = Field(..., description="所有钱包总余额")
    total_earned: int = Field(..., description="所有钱包累计获得")
    total_spent: int = Field(..., description="所有钱包累计消费")
    transaction_count: int = Field(..., description="交易总数")
    active_wallets: int = Field(..., description="活跃钱包数")
