<script setup lang="ts">
/* eslint-disable @typescript-eslint/no-use-before-define, no-nested-ternary, complexity */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import {
  NAlert,
  NAvatar,
  NButton,
  NCard,
  NDatePicker,
  NEmpty,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NModal,
  NPagination,
  NProgress,
  NScrollbar,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  useDialog,
  useMessage
} from 'naive-ui';
import {
  type AgentTaskCreate,
  type TaskComment,
  cancelAgentTask,
  createAgentTask,
  createTaskComment,
  deleteAgentTask,
  deleteTaskComment,
  fetchAgentTaskDetail,
  fetchAgentTaskList,
  fetchAgentTaskStatistics,
  fetchOnlineAgents,
  fetchTaskComments,
  fetchTransactions,
  fetchWalletStatistics
} from '@/service/api/mission-center';

const message = useMessage();
const dialog = useDialog();

// 进度历史记录
interface ProgressHistory {
  percentage: number;
  step: string;
  message?: string; // AI 的思考文本/内心独白
  timestamp: string;
}

// 类型定义
interface Task {
  task_id: string;
  title: string;
  description?: string;
  priority: string;
  assignee?: string; // 改为可选，支持 Agent 主动认领
  deadline?: string;
  status: string;
  progress_percentage: number;
  current_step: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  result?: any;
  error?: any;
  logs: any[];
  progressHistory: ProgressHistory[];
  reward?: number; // 🎯 金币奖励
  acceptance_criteria?: string[]; // 🎯 验收标准
}

interface AgentInfo {
  agentId: string;
  name: string;
  agentType: string;
  capabilities?: string[];
  status: 'idle' | 'busy' | 'offline';
  currentTaskCount: number;
  lastHeartbeat: string;
  registeredAt?: string;
}

// WebSocket 连接
let ws: WebSocket | null = null;

// 响应式状态
const tasks = ref<Task[]>([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);
const statistics = ref<Record<string, number>>({});
const agents = ref<AgentInfo[]>([]);
const wsConnected = ref(false);
const wsReconnecting = ref(false);

// 🎯 金币统计相关
const coinStatsPeriod = ref<'day' | 'week' | 'month'>('day'); // 时间周期：日/周/月
const coinStats = ref({
  total: 0, // 全部金币（已完成+待完成）
  completed: 0, // 已完成金币
  pending: 0, // 待完成金币
  rate: 0 // 金币交易数
});

// 对话框状态
const showCreateDialog = ref(false);
const showDetailDialog = ref(false);
const selectedTask = ref<Task | null>(null);
const creating = ref(false);
const refreshing = ref(false);

// 评论相关状态
const comments = ref<TaskComment[]>([]);
const commentsLoading = ref(false);
const newComment = ref('');
const activeTab = ref('conversation'); // 'conversation' | 'comments'

// 表单数据
const newTask = reactive({
  title: '',
  description: '',
  priority: 'medium',
  deadline: null as number | null,
  acceptanceCriteriaText: '', // 🎯 验收标准（文本格式，按行分割）
  reward: 10 // 🎯 金币奖励（默认10金币）
});

// 搜索和筛选
const searchKeyword = ref('');
const statusFilter = ref<string | null>(null);
// priorityFilter 已移除 - 不再支持优先级筛选

// 动画控制
const taskAnimationMap = ref<Record<string, boolean>>({});

// 常量定义
// priorityOptions 已移除 - 不再支持优先级
const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '已分配', value: 'assigned' },
  { label: '进行中', value: 'in_progress' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
  { label: '已取消', value: 'cancelled' }
];

// 状态映射
const statusLabels: Record<string, string> = {
  pending: '待处理',
  assigned: '已分配',
  in_progress: '进行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消'
};

const statusTypes: Record<string, any> = {
  pending: 'info',
  assigned: 'default',
  in_progress: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'info'
};

const priorityLabels: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  urgent: '紧急'
};

const priorityTypes: Record<string, any> = {
  low: 'info',
  medium: 'default',
  high: 'warning',
  urgent: 'error'
};

// 左侧栏统计卡片配置 (紧凑版)
const statisticsConfig = [
  { key: 'pending', label: '待处理', icon: '⏰', color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { key: 'assigned', label: '已分配', icon: '📋', color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
  { key: 'in_progress', label: '进行中', icon: '🚀', color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' },
  { key: 'completed', label: '已完成', icon: '✅', color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' },
  { key: 'failed', label: '失败', icon: '❌', color: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' },
  { key: 'cancelled', label: '已取消', icon: '🚫', color: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)' }
];

// 过滤后的任务
const filteredTasks = computed(() => {
  let result = [...tasks.value];

  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase();
    result = result.filter(
      task =>
        task.task_id.toLowerCase().includes(keyword) ||
        task.title.toLowerCase().includes(keyword) ||
        task.description.toLowerCase().includes(keyword) ||
        (task.assignee && task.assignee.toLowerCase().includes(keyword))
    );
  }

  if (statusFilter.value) {
    result = result.filter(task => task.status === statusFilter.value);
  }

  // 移除了优先级筛选

  return result;
});

// 判断任务是否可以取消
const canCancel = (status: string) => {
  return ['pending', 'assigned', 'in_progress'].includes(status);
};

// API 方法
const fetchTasks = async () => {
  loading.value = true;
  try {
    const offset = (currentPage.value - 1) * pageSize.value;
    const { error, data } = await fetchAgentTaskList({
      limit: pageSize.value,
      offset
    });

    if (!error && data) {
      // 确保 progressHistory 字段存在
      tasks.value = data.rows.map(task => ({
        ...task,
        progressHistory: task.progressHistory || []
      }));
      total.value = data.total;
      // 🎯 计算金币统计
      calculateCoinStats();
    }
  } catch (error) {
    message.error('获取任务列表失败');
    console.error(error);
  } finally {
    loading.value = false;
  }
};

const fetchStatistics = async () => {
  try {
    const { error, data } = await fetchAgentTaskStatistics();

    if (!error && data) {
      statistics.value = data.by_status;
    }
  } catch (error) {
    console.error('获取统计信息失败', error);
  }
};

// 🎯 计算金币统计
const calculateCoinStats = async () => {
  try {
    // 调用钱包统计 API
    const { error: walletError, data: walletData } = await fetchWalletStatistics();

    if (!walletError && walletData) {
      // 调用交易流水 API
      const { data: transactionData } = await fetchTransactions({ limit: 1 });

      coinStats.value = {
        total: walletData.total_balance, // 所有 Agent 钱包里的金币总计
        completed: walletData.total_earned, // 已获得金币
        pending: walletData.total_balance, // 待完成 = 当前余额
        rate: transactionData?.total || 0 // 金币交易数（交易流水数量）
      };
    }
  } catch (error) {
    console.error('获取钱包统计失败:', error);
  }
};

const fetchOnlineAgentsData = async () => {
  try {
    const { error, data } = await fetchOnlineAgents();

    if (!error && data) {
      // 更新 agents 列表，映射 status
      agents.value = data.agents.map(agent => ({
        agentId: agent.agentId,
        name: agent.name,
        agentType: agent.agentType,
        capabilities: agent.capabilities,
        status: (agent.status === 'online' ? 'idle' : agent.status) as 'idle' | 'busy' | 'offline',
        currentTaskCount: 0,
        lastHeartbeat: agent.lastHeartbeat,
        registeredAt: agent.registeredAt
      }));

      console.log(`已加载 ${data.agents.length} 个在线 Agent`);
    }
  } catch (error) {
    console.error('获取在线 Agent 失败', error);
  }
};

const createTask = async () => {
  if (!newTask.title || !newTask.description) {
    message.warning('请填写任务标题和描述');
    return;
  }

  creating.value = true;
  try {
    // 处理验收标准：按行分割转换为数组
    const acceptanceCriteria = newTask.acceptanceCriteriaText
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0);

    const taskData: AgentTaskCreate = {
      title: newTask.title,
      description: newTask.description,
      priority: 'medium' as any, // 固定为 medium
      // 不指定 assignee，让 Agent 主动认领
      assignee: undefined,
      deadline: newTask.deadline ? new Date(newTask.deadline).toISOString() : undefined,
      // 🎯 新增字段
      acceptance_criteria: acceptanceCriteria.length > 0 ? acceptanceCriteria : undefined,
      reward: newTask.reward
    };
    const { error } = await createAgentTask(taskData);

    if (!error) {
      message.success(`✅ 任务已发布到任务池，${newTask.reward} 💰 金币！等待 Agent 认领中...`, { duration: 4000 });
      showCreateDialog.value = false;
      Object.assign(newTask, {
        title: '',
        description: '',
        deadline: null,
        acceptanceCriteriaText: '',
        reward: 10
      });
      fetchTasks();
      fetchStatistics();
    } else {
      message.error(error.message || '创建任务失败');
    }
  } catch (error: any) {
    message.error(error?.message || '创建任务失败');
    console.error(error);
  } finally {
    creating.value = false;
  }
};

const viewTask = async (task: Task) => {
  selectedTask.value = task;
  showDetailDialog.value = true;
  // 加载评论
  await loadComments();
};

const refreshTask = async () => {
  if (!selectedTask.value) return;

  refreshing.value = true;
  try {
    const { error, data } = await fetchAgentTaskDetail(selectedTask.value.task_id);

    if (!error && data) {
      selectedTask.value = data;
      message.success('任务已刷新');
    }
  } catch (error) {
    message.error('刷新任务失败');
    console.error(error);
  } finally {
    refreshing.value = false;
  }
};

// ========== 评论相关方法 ==========

// 加载任务评论
const loadComments = async () => {
  if (!selectedTask.value) return;

  commentsLoading.value = true;
  try {
    const { error, data } = await fetchTaskComments(selectedTask.value.task_id);

    if (!error && data) {
      comments.value = data.comments || [];
    }
  } catch (error) {
    console.error('加载评论失败:', error);
  } finally {
    commentsLoading.value = false;
  }
};

// 发表评论
const handleAddComment = async () => {
  if (!newComment.value.trim() || !selectedTask.value) return;

  try {
    const { error } = await createTaskComment(selectedTask.value.task_id, {
      content: newComment.value,
      comment_type: 'comment'
    });

    if (!error) {
      newComment.value = '';
      await loadComments();
      message.success('评论已发表');
    } else {
      message.error('发表评论失败');
    }
  } catch (error: any) {
    message.error(error?.message || '发表评论失败');
    console.error(error);
  }
};

// 删除评论
const handleDeleteComment = async (commentId: number) => {
  dialog.warning({
    title: '删除评论',
    content: '确定要删除这条评论吗？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const { error } = await deleteTaskComment(commentId);

        if (!error) {
          await loadComments();
          message.success('评论已删除');
        } else {
          message.error('删除评论失败');
        }
      } catch (error: any) {
        message.error(error?.message || '删除评论失败');
        console.error(error);
      }
    }
  });
};

const cancelTask = (task: Task) => {
  dialog.warning({
    title: '取消任务',
    content: `确定要取消任务 "${task.title}" 吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const { error } = await cancelAgentTask(task.task_id, '用户手动取消');

        if (!error) {
          message.success('任务已取消');
          fetchTasks();
          fetchStatistics();
        }
      } catch (error) {
        message.error('取消任务失败');
        console.error(error);
      }
    }
  });
};

const deleteTaskHandler = (task: Task) => {
  dialog.error({
    title: '删除任务',
    content: `确定要删除任务 "${task.title}" 吗？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const { error } = await deleteAgentTask(task.task_id);

        if (!error) {
          message.success('任务已删除');
          fetchTasks();
          fetchStatistics();
        }
      } catch (error) {
        message.error('删除任务失败');
        console.error(error);
      }
    }
  });
};

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString('zh-CN');
};

// 格式化时间（只显示时分秒）
const formatTime = (dateStr: string) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleTimeString('zh-CN', { hour12: false });
};

// 根据进度获取标签类型
const getProgressType = (percentage: number) => {
  if (percentage >= 100) return 'success';
  if (percentage >= 80) return 'info';
  if (percentage >= 50) return 'warning';
  return 'default';
};

const clearFilters = () => {
  searchKeyword.value = '';
  statusFilter.value = null;
  // priorityFilter 已移除
};

// WebSocket
const initWebSocket = () => {
  wsReconnecting.value = true;

  // 从环境变量获取WebSocket地址
  const wsUrl = import.meta.env.VITE_SERVICE_BASE_URL
    ? import.meta.env.VITE_SERVICE_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://')
    : 'ws://localhost:7377';

  ws = new WebSocket(`${wsUrl}/ws/hub`);

  ws.onopen = () => {
    console.log('WebSocket 连接已建立');
    wsConnected.value = true;
    wsReconnecting.value = false;
    // 连接成功后主动查询在线 Agent
    fetchOnlineAgentsData();
  };

  ws.onmessage = event => {
    try {
      const msg = JSON.parse(event.data);

      if (msg.type === 'task_progress' || msg.type === 'task:progress') {
        const taskData = msg.payload || msg.data;
        const index = tasks.value.findIndex(t => t.task_id === taskData.taskId || t.task_id === taskData.task_id);

        if (index !== -1) {
          // 触发动画
          taskAnimationMap.value[tasks.value[index].task_id] = true;

          // 保存进度历史（包含 AI 的思考文本）
          const newProgressEntry = {
            percentage: taskData.progress,
            step: taskData.currentStep || taskData.current_step || '处理中...',
            message: taskData.message || '', // AI 的思考文本
            timestamp: new Date().toISOString()
          };

          tasks.value[index] = {
            ...tasks.value[index],
            status: taskData.status,
            progress_percentage: taskData.progress,
            current_step: taskData.currentStep || taskData.current_step,
            progressHistory: [...(tasks.value[index].progressHistory || []), newProgressEntry]
          };

          // 500ms 后移除动画标记
          setTimeout(() => {
            taskAnimationMap.value[tasks.value[index]?.task_id] = false;
          }, 500);
        }
        fetchStatistics();
      }

      if (msg.type === 'task_completion' || msg.type === 'task:complete') {
        const taskData = msg.payload || msg.data;
        const index = tasks.value.findIndex(t => t.task_id === taskData.taskId || t.task_id === taskData.task_id);

        if (index !== -1) {
          tasks.value[index] = {
            ...tasks.value[index],
            status: taskData.status === 'COMPLETED' ? 'completed' : 'failed'
          };
        } else {
          fetchTasks();
        }
        fetchStatistics();
        message.success(`任务 "${taskData.taskId || taskData.task_id}" 已完成`);
      }

      if (msg.type === 'agent:register') {
        const agentData = msg.payload || msg.data;
        const existingIndex = agents.value.findIndex(a => a.agentId === agentData.agentId);

        if (existingIndex === -1) {
          agents.value.push({
            agentId: agentData.agentId,
            name: agentData.name,
            agentType: agentData.agentType,
            capabilities: agentData.capabilities || [],
            status: 'idle',
            currentTaskCount: 0,
            lastHeartbeat: new Date().toISOString(),
            registeredAt: new Date().toISOString()
          });
          message.success(`Agent "${agentData.name}" 已注册`);
        }
      }

      if (msg.type === 'agent:heartbeat') {
        const agentData = msg.payload || msg.data;
        const index = agents.value.findIndex(a => a.agentId === agentData.agentId);

        if (index !== -1) {
          agents.value[index].status = agentData.status || 'idle';
          agents.value[index].currentTaskCount = agentData.currentTaskCount || 0;
          agents.value[index].lastHeartbeat = new Date().toISOString();
        }
      }

      if (msg.type === 'agent:unregister') {
        const agentData = msg.payload || msg.data;
        const index = agents.value.findIndex(a => a.agentId === agentData.agentId);

        if (index !== -1) {
          agents.value[index].status = 'offline';
          message.warning(`Agent "${agents.value[index].name}" 已离线`);
        }
      }
    } catch (error) {
      console.error('处理 WebSocket 消息失败', error);
    }
  };

  ws.onerror = error => {
    console.error('WebSocket 错误', error);
  };

  ws.onclose = () => {
    console.log('WebSocket 连接已关闭');
    wsConnected.value = false;
    wsReconnecting.value = false;
    setTimeout(initWebSocket, 5000);
  };
};

onMounted(() => {
  fetchTasks();
  fetchStatistics();
  calculateCoinStats(); // 🎯 计算金币统计
  initWebSocket();
});

// 🎯 监听周期变化，重新计算金币统计
watch(coinStatsPeriod, () => {
  calculateCoinStats();
});

onUnmounted(() => {
  if (ws) {
    ws.close();
  }
});
</script>

<template>
  <div class="task-management">
    <!-- 顶部导航 -->
    <div class="page-header">
      <div class="header-left">
        <div class="page-title">
          <NIcon size="28" :component="null">
            <svg viewBox="0 0 24 24" width="28" height="28">
              <path
                fill="currentColor"
                d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"
              />
            </svg>
          </NIcon>
          <h1>任务大厅</h1>
        </div>
        <div class="connection-status">
          <NTag :type="wsConnected ? 'success' : wsReconnecting ? 'warning' : 'error'" size="small" round>
            <template #icon>
              <div class="status-indicator" :class="{ connected: wsConnected, reconnecting: wsReconnecting }"></div>
            </template>
            {{ wsConnected ? '已连接' : wsReconnecting ? '重新连接中...' : '未连接' }}
          </NTag>
        </div>
      </div>
      <div class="header-right">
        <NButton type="primary" class="create-btn" @click="showCreateDialog = true">
          <template #icon>
            <NIcon>
              <svg viewBox="0 0 24 24" width="18" height="18">
                <path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
              </svg>
            </NIcon>
          </template>
          创建任务
        </NButton>
      </div>
    </div>

    <!-- 主内容区 - 左右分栏布局 -->
    <div class="main-content">
      <!-- 左侧栏: 控制面板 (320px) -->
      <div class="left-sidebar">
        <!-- 页面标题和 WebSocket 状态 -->
        <!--
 <div class="sidebar-header">
          <h1 class="page-title">任务大厅</h1>
          <div class="status-badge">
            <div class="status-dot" :class="{ online: wsConnected }"></div>
            <span class="status-text">{{ wsConnected ? 'Hub 已连接' : 'Hub 未连接' }}</span>
          </div>
        </div> 
-->

        <!-- 统计卡片 - 紧凑 2x3 布局 -->
        <NCard class="stats-card">
          <div class="stats-grid-compact">
            <div v-for="stat in statisticsConfig" :key="stat.key" class="stat-item-compact">
              <div class="stat-icon-compact" :style="{ background: stat.color }">
                <span>{{ stat.icon }}</span>
              </div>
              <div class="stat-content-compact">
                <div class="stat-value-compact">{{ statistics[stat.key] || 0 }}</div>
                <div class="stat-label-compact">{{ stat.label }}</div>
              </div>
            </div>
          </div>
        </NCard>

        <!-- 🎯 金币统计面板 -->
        <NCard class="coin-stats-card">
          <template #header>
            <div class="coin-stats-header">
              <span class="coin-stats-title">💰 金币统计</span>
              <NSelect
                v-model:value="coinStatsPeriod"
                :options="[
                  { label: '按日', value: 'day' },
                  { label: '按周', value: 'week' },
                  { label: '按月', value: 'month' }
                ]"
                size="small"
                style="width: 100px"
              />
            </div>
          </template>
          <div class="coin-stats-content">
            <div class="coin-stat-item total">
              <div class="coin-stat-label">全部金币</div>
              <div class="coin-stat-value">{{ coinStats.total }}</div>
              <div class="coin-stat-unit">💰</div>
            </div>
            <div class="coin-stats-row">
              <div class="coin-stat-item completed">
                <div class="coin-stat-label">已完成</div>
                <div class="coin-stat-value">{{ coinStats.completed }}</div>
                <div class="coin-stat-unit">✅</div>
              </div>
              <div class="coin-stat-item pending">
                <div class="coin-stat-label">待完成</div>
                <div class="coin-stat-value">{{ coinStats.pending }}</div>
                <div class="coin-stat-unit">⏳</div>
              </div>
            </div>
            <div class="coin-stat-item rate">
              <div class="coin-stat-label">交易数</div>
              <div class="coin-stat-value">{{ coinStats.rate }}</div>
              <div class="coin-stat-unit">笔</div>
            </div>
          </div>
        </NCard>

        <!-- 在线 Agent 列表 -->
        <NCard class="agents-card">
          <template #header>
            <div class="agents-card-header">
              <span>在线 Agent</span>
              <NTag :type="wsConnected ? 'success' : 'error'" size="small" round>
                {{ agents.filter(a => a.status !== 'offline').length }} 在线
              </NTag>
            </div>
          </template>

          <NScrollbar style="max-height: 280px">
            <div v-if="agents.length > 0" class="agent-list-compact">
              <div
                v-for="agent in agents"
                :key="agent.agentId"
                class="agent-item-compact"
                :class="{ offline: agent.status === 'offline' }"
              >
                <NAvatar
                  round
                  size="small"
                  :style="{
                    background: agent.status === 'offline' ? 'var(--color-text-tertiary)' : agent.status === 'busy' ? 'var(--color-warning)' : '#10b981'
                  }"
                >
                  {{ agent.name?.charAt(0).toUpperCase() || 'A' }}
                </NAvatar>
                <div class="agent-info-compact">
                  <div class="agent-name-compact">{{ agent.name }}</div>
                  <div class="agent-status-compact">
                    <span :class="`status-text-${agent.status}`">
                      {{ { idle: '空闲', busy: '忙碌', offline: '离线' }[agent.status] }}
                    </span>
                    <span v-if="agent.currentTaskCount > 0" class="task-count-compact">
                      · {{ agent.currentTaskCount }} 任务
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <NEmpty v-else description="暂无在线 Agent" size="small" />
          </NScrollbar>
        </NCard>

        <!-- 连接信息 -->
        <NCard class="connection-card">
          <div class="connection-info-compact">
            <div class="connection-item">
              <span class="connection-label">WebSocket</span>
              <span class="connection-value" :class="{ connected: wsConnected }">
                {{ wsConnected ? '已连接' : '未连接' }}
              </span>
            </div>
            <div class="connection-item">
              <span class="connection-label">在线 Agent</span>
              <span class="connection-value">
                {{ agents.filter(a => a.status !== 'offline').length }} / {{ agents.length }}
              </span>
            </div>
            <div class="connection-item">
              <span class="connection-label">总任务数</span>
              <span class="connection-value">{{ filteredTasks.length }}</span>
            </div>
          </div>
        </NCard>
      </div>

      <!-- 右侧内容区: 任务列表 (flex: 1) -->
      <div class="right-content">
        <!-- 搜索和筛选工具栏 -->
        <NCard class="toolbar-card-compact">
          <div class="toolbar-compact">
            <div class="search-group-compact">
              <NInput
                v-model:value="searchKeyword"
                placeholder="搜索任务 ID、标题、描述..."
                clearable
                class="search-input-compact"
              >
                <template #prefix>
                  <span style="font-size: 16px">🔍</span>
                </template>
              </NInput>
              <NSelect
                v-model:value="statusFilter"
                :options="statusOptions"
                placeholder="状态筛选"
                clearable
                style="width: 130px"
              />
              <NButton v-if="searchKeyword || statusFilter" quaternary type="info" @click="clearFilters">
                清除筛选
              </NButton>
            </div>
            <div class="toolbar-info">
              <span class="task-count-info">共 {{ filteredTasks.length }} 个任务</span>
            </div>
          </div>
        </NCard>

        <!-- 任务列表 - 🎯 卡片式布局 -->
        <NCard class="task-list-card-compact">
          <!-- 🎯 任务卡片网格 -->
          <div v-if="!loading && filteredTasks.length > 0" class="task-cards-grid">
            <div
              v-for="task in filteredTasks"
              :key="task.task_id"
              class="task-card"
              :class="{ 'task-card-active': task.status === 'in_progress' }"
            >
              <!-- 卡片头部 -->
              <div class="task-card-header">
                <div class="task-card-id">
                  <span class="task-id-text">{{ task.task_id }}</span>
                </div>
                <NTag :type="statusTypes[task.status] || 'default'" size="small">
                  {{ statusLabels[task.status] }}
                </NTag>
              </div>

              <!-- 卡片内容 -->
              <div class="task-card-body">
                <h3 class="task-card-title">{{ task.title }}</h3>
                <p class="task-card-description">{{ task.description || '暂无描述' }}</p>

                <!-- 🎯 金币奖励和验收标准 -->
                <div class="task-card-rewards">
                  <div v-if="task.reward" class="task-reward-badge">
                    <span class="reward-icon">💰</span>
                    <span class="reward-value">{{ task.reward }}</span>
                  </div>
                  <div
                    v-if="task.acceptance_criteria && task.acceptance_criteria.length > 0"
                    class="task-criteria-badge"
                  >
                    <span class="criteria-icon">✓</span>
                    <span class="criteria-count">{{ task.acceptance_criteria.length }} 项验收标准</span>
                  </div>
                </div>

                <!-- 进度条 -->
                <!-- 进度信息 -->
                <div class="task-card-progress-simple">
                  <span class="progress-percent">{{ task.progress_percentage }}%</span>
                  <span v-if="task.current_step" class="progress-status">{{ task.current_step }}</span>
                  <span v-else class="progress-status">待处理</span>
                  <span class="progress-time">{{ new Date(task.created_at).toLocaleString('zh-CN') }}</span>
                </div>
              </div>

              <!-- 卡片操作 -->
              <div class="task-card-actions">
                <NButton size="small" type="info" ghost @click="viewTask(task)">查看</NButton>
                <NButton v-if="canCancel(task.status)" size="small" type="warning" ghost @click="cancelTask(task)">
                  取消
                </NButton>
                <NPopconfirm @positive-click="() => deleteTaskHandler(task)">
                  <template #trigger>
                    <NButton size="small" type="error" ghost>删除</NButton>
                  </template>
                  <span>确定要删除此任务吗？</span>
                </NPopconfirm>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <NEmpty v-else-if="!loading" description="暂无任务" size="large" style="padding: 60px 0" />

          <!-- 加载状态 -->
          <NSpin v-else size="large" style="padding: 60px 0; display: flex; justify-content: center">
            <template #description>加载任务列表中...</template>
          </NSpin>

          <!-- 分页 -->
          <div v-if="filteredTasks.length > 0" class="pagination-wrapper-compact">
            <NPagination
              v-model:page="currentPage"
              v-model:page-size="pageSize"
              :item-count="total"
              :page-sizes="[10, 20, 50, 100]"
              show-size-picker
              @update:page="fetchTasks"
              @update:page-size="fetchTasks"
            />
          </div>
        </NCard>
      </div>
    </div>

    <!-- 创建任务对话框 -->
    <NModal
      v-model:show="showCreateDialog"
      preset="card"
      title="创建新任务"
      style="width: 600px"
      :mask-closable="!creating"
      :closable="!creating"
    >
      <NForm :model="newTask" label-placement="left" label-width="120px">
        <NFormItem label="任务标题" required>
          <NInput v-model:value="newTask.title" placeholder="请输入任务标题" />
        </NFormItem>
        <NFormItem label="任务描述" required>
          <NInput v-model:value="newTask.description" type="textarea" :rows="4" placeholder="请详细描述你的需求..." />
        </NFormItem>
        <NFormItem label="验收标准">
          <NInput
            v-model:value="newTask.acceptanceCriteriaText"
            type="textarea"
            :rows="3"
            placeholder="明确任务完成的判断条件（每行一条）&#10;例如：&#10;1. 故事必须有趣且完整&#10;2. 体现程序员的职业特点&#10;3. 字数不少于300字"
          />
        </NFormItem>
        <NFormItem label="金币奖励">
          <NInputNumber
            v-model:value="newTask.reward"
            :min="1"
            :max="1000"
            placeholder="设置金币奖励"
            style="width: 100%"
          >
            <template #suffix>
              <span style="color: var(--color-warning)">💰</span>
            </template>
          </NInputNumber>
        </NFormItem>
        <NFormItem label="截止时间">
          <NDatePicker
            v-model:value="newTask.deadline"
            type="datetime"
            placeholder="选择截止时间（可选）"
            style="width: 100%"
            value-format="yyyy-MM-dd HH:mm:ss"
          />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton :disabled="creating" @click="showCreateDialog = false">取消</NButton>
          <NButton type="primary" :loading="creating" @click="createTask">创建</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- 任务详情对话框 - 重新设计 -->
    <NModal
      v-model:show="showDetailDialog"
      preset="card"
      title=""
      style="width: 1400px; max-width: 95vw"
      :bordered="false"
      :mask-closable="true"
    >
      <template #header>
        <div class="detail-header">
          <div class="detail-title">
            <h2>任务详情</h2>
            <NTag v-if="selectedTask" :type="statusTypes[selectedTask.status] || 'default'" size="large" round>
              {{ statusLabels[selectedTask.status] || selectedTask.status }}
            </NTag>
          </div>
        </div>
      </template>

      <NSpin :show="refreshing" size="large">
        <div v-if="selectedTask" class="task-detail-content">
          <!-- 左栏：任务信息 + 进度 -->
          <div class="left-column">
            <!-- 任务基本信息卡片 -->
            <div class="info-card">
              <div class="info-card-header">
                <div class="task-title">{{ selectedTask.title }}</div>
                <NTag
                  v-if="selectedTask.priority"
                  :type="priorityTypes[selectedTask.priority] || 'default'"
                  size="small"
                >
                  {{ priorityLabels[selectedTask.priority] || selectedTask.priority }}
                </NTag>
              </div>
              <div class="info-card-body">
                <div class="task-description">{{ selectedTask.description }}</div>
                <div class="task-meta">
                  <div class="meta-item">
                    <span class="meta-label">任务 ID</span>
                    <NTag size="tiny" type="info">{{ selectedTask.task_id.slice(0, 20) }}...</NTag>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">分配给</span>
                    <NTag size="tiny" type="primary">{{ selectedTask.assignee }}</NTag>
                  </div>
                </div>
              </div>
            </div>

            <!-- 进度和时间线卡片 -->
            <div class="progress-card">
              <div class="progress-header">
                <div class="progress-title">
                  <h3>执行进度</h3>
                  <NTag :type="getProgressType(selectedTask.progress_percentage)" size="medium" round>
                    {{ selectedTask.progress_percentage }}%
                  </NTag>
                </div>
                <div class="progress-bar-wrapper">
                  <NProgress
                    :percentage="selectedTask.progress_percentage"
                    :status="
                      selectedTask.status === 'failed'
                        ? 'error'
                        : selectedTask.status === 'completed'
                          ? 'success'
                          : 'default'
                    "
                    :height="8"
                    :border-radius="4"
                    :show-indicator="false"
                  />
                </div>
              </div>

              <!-- 时间信息 -->
              <div class="time-info">
                <div class="time-item">
                  <span class="time-label">创建</span>
                  <span class="time-value">{{ formatDateTime(selectedTask.created_at) }}</span>
                </div>
                <div class="time-item">
                  <span class="time-label">更新</span>
                  <span class="time-value">{{ formatDateTime(selectedTask.updated_at) }}</span>
                </div>
                <div v-if="selectedTask.completed_at" class="time-item">
                  <span class="time-label">完成</span>
                  <span class="time-value">{{ formatDateTime(selectedTask.completed_at) }}</span>
                </div>
              </div>
            </div>

            <!-- 执行结果 -->
            <div v-if="selectedTask.result" class="result-card">
              <div class="result-header">
                <h3>✨ 执行结果</h3>
              </div>
              <div class="result-content">
                <pre class="result-json">{{ JSON.stringify(selectedTask.result, null, 2) }}</pre>
              </div>
            </div>

            <!-- 错误信息 -->
            <div v-if="selectedTask.error" class="error-card">
              <NAlert type="error" :title="selectedTask.error.message || '执行错误'">
                {{ selectedTask.error.stack || '' }}
              </NAlert>
            </div>
          </div>

          <!-- 右栏：Tab 切换（AI 对话流 + 评论） -->
          <div class="right-column">
            <NTabs v-model:value="activeTab" type="segment" animated>
              <!-- AI 对话流 Tab -->
              <NTabPane name="conversation" tab="🤖 AI 对话流">
                <template #tab>
                  <NSpace align="center" :size="8">
                    <span>🤖 AI 对话流</span>
                    <NTag
                      v-if="selectedTask.progressHistory && selectedTask.progressHistory.length > 0"
                      type="success"
                      size="small"
                      round
                    >
                      {{ selectedTask.progressHistory.length }}
                    </NTag>
                  </NSpace>
                </template>

                <div
                  v-if="selectedTask.progressHistory && selectedTask.progressHistory.length > 0"
                  class="conversation-card"
                >
                  <div class="conversation-flow">
                    <div
                      v-for="(item, index) in selectedTask.progressHistory"
                      :key="index"
                      class="conversation-message"
                      :class="{ 'is-complete': item.percentage === 100 }"
                    >
                      <!-- 连接线 -->
                      <div v-if="index > 0" class="message-connector"></div>

                      <div class="message-main">
                        <div class="message-icon">
                          <span class="icon-emoji">🤖</span>
                          <span class="icon-progress">{{ item.percentage }}%</span>
                        </div>
                        <div class="message-body">
                          <div class="message-meta-line">
                            <span class="message-time">{{ formatTime(item.timestamp) }}</span>
                            <NTag type="info" size="small" round>{{ item.step }}</NTag>
                          </div>
                          <div v-if="item.message" class="message-text">
                            {{ item.message }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <NEmpty v-else description="暂无对话记录" size="small" />
              </NTabPane>

              <!-- 评论 Tab -->
              <NTabPane name="comments" tab="💬 评论">
                <template #tab>
                  <NSpace align="center" :size="8">
                    <span>💬 评论</span>
                    <NTag type="info" size="small" round>{{ comments.length }}</NTag>
                  </NSpace>
                </template>

                <div class="comments-card">
                  <!-- 添加评论 -->
                  <div class="add-comment">
                    <NInput
                      v-model="newComment"
                      type="textarea"
                      placeholder="添加评论..."
                      :rows="3"
                      @keydown.enter.ctrl="handleAddComment"
                    />
                    <div class="comment-actions">
                      <NButton type="primary" size="small" :disabled="!newComment.trim()" @click="handleAddComment">
                        发表评论
                      </NButton>
                    </div>
                  </div>

                  <!-- 评论列表 -->
                  <NSpin :show="commentsLoading">
                    <div v-if="comments.length > 0" class="comments-list">
                      <div v-for="comment in comments" :key="comment.id" class="comment-item">
                        <div class="comment-header">
                          <NSpace align="center" :size="8">
                            <NText strong>{{ comment.agent_id || comment.user_id || '匿名' }}</NText>
                            <NTag v-if="comment.comment_type === 'plan'" type="success" size="tiny">计划</NTag>
                            <NTag v-if="comment.comment_type === 'claim'" type="info" size="tiny">认领</NTag>
                            <NText depth="3" style="font-size: 12px">
                              {{ formatDateTime(comment.created_at) }}
                            </NText>
                          </NSpace>
                          <NButton text size="tiny" @click="handleDeleteComment(comment.id)">删除</NButton>
                        </div>
                        <div class="comment-text">{{ comment.content }}</div>
                      </div>
                    </div>
                    <NEmpty v-else description="暂无评论" size="small" />
                  </NSpin>
                </div>
              </NTabPane>
            </NTabs>
          </div>
        </div>
      </NSpin>

      <template #footer>
        <NSpace justify="end" :size="12">
          <NButton size="large" @click="showDetailDialog = false">关闭</NButton>
          <NButton type="primary" size="large" :loading="refreshing" @click="refreshTask">刷新</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped lang="scss">
.task-management {
  padding: 24px;
  min-height: 100%;
  background: #f8fafc;
}

// 页面头部
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .page-title {
      display: flex;
      align-items: center;
      gap: 12px;

      h1 {
        margin: 0;
        font-size: 24px;
        font-weight: 600;
        color: #1e293b;
      }

      :deep(.n-icon) {
        color: var(--color-primary);
      }
    }

    .connection-status {
      .status-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--color-danger);
        transition: all 0.3s ease;

        &.connected {
          background: #10b981;
          box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
        }

        &.reconnecting {
          background: var(--color-warning);
          animation: pulse 1s ease-in-out infinite;
        }
      }
    }
  }

  .create-btn {
    font-weight: 500;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
    transition: all 0.2s ease;

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
  }
}

// 统计卡片
.stats-section {
  margin-bottom: 24px;

  .stat-card {
    --stat-color: var(--color-primary);
    --stat-bg: rgba(59, 130, 246, 0.1);
    transition: all 0.3s ease;
    border: none;
    background: linear-gradient(135deg, #fff 0%, var(--stat-bg) 100%);

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
    }

    .stat-content {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;

      .stat-icon {
        width: 48px;
        height: 48px;
        border-radius: 12px;
        background: var(--stat-bg);
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--stat-color);
      }

      .stat-info {
        .stat-value {
          font-size: 28px;
          font-weight: 700;
          color: var(--stat-color);
          line-height: 1.2;
        }

        .stat-label {
          font-size: 13px;
          color: #64748b;
          margin-top: 2px;
        }
      }
    }

    .stat-bar {
      height: 4px;
      background: #e2e8f0;
      border-radius: 2px;
      overflow: hidden;

      .stat-bar-fill {
        height: 100%;
        background: var(--stat-color);
        border-radius: 2px;
        transition: width 0.5s ease;
      }
    }
  }
}

// 主内容区 - 左右分栏布局
.main-content {
  display: flex;
  gap: 24px;
  align-items: flex-start;

  // 左侧栏: 控制面板 (320px)
  .left-sidebar {
    width: 320px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 20px;
    position: sticky;
    top: 24px;

    .sidebar-header {
      .page-title {
        margin: 0 0 12px 0;
        font-size: 22px;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      .status-badge {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--color-danger);
          transition: all 0.3s ease;

          &.online {
            background: #10b981;
            box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
          }
        }

        .status-text {
          font-size: 13px;
          color: #64748b;
          font-weight: 500;
        }
      }
    }

    .stats-card {
      border: none;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

      .stats-grid-compact {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;

        .stat-item-compact {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px;
          background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
          border-radius: 8px;
          transition: all 0.2s ease;

          &:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
          }

          .stat-icon-compact {
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            font-size: 18px;
            flex-shrink: 0;
          }

          .stat-content-compact {
            flex: 1;
            min-width: 0;

            .stat-value-compact {
              font-size: 20px;
              font-weight: 700;
              color: #1e293b;
              line-height: 1;
            }

            .stat-label-compact {
              font-size: 11px;
              color: #64748b;
              margin-top: 2px;
            }
          }
        }
      }
    }

    .agents-card {
      border: none;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

      .agents-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 600;
        color: #1e293b;
      }

      .agent-list-compact {
        display: flex;
        flex-direction: column;
        gap: 8px;

        .agent-item-compact {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px;
          background: #f8fafc;
          border-radius: 8px;
          transition: all 0.2s ease;

          &:hover {
            background: #f1f5f9;
            transform: translateX(2px);
          }

          &.offline {
            opacity: 0.5;
          }

          .agent-info-compact {
            flex: 1;
            min-width: 0;

            .agent-name-compact {
              font-size: 13px;
              font-weight: 600;
              color: #1e293b;
              margin-bottom: 2px;
            }

            .agent-status-compact {
              font-size: 11px;
              color: #64748b;

              .status-text-idle {
                color: #10b981;
              }

              .status-text-busy {
                color: var(--color-warning);
              }

              .status-text-offline {
                color: #94a3b8;
              }

              .task-count-compact {
                color: #64748b;
              }
            }
          }
        }
      }
    }

    .connection-card {
      border: none;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

      .connection-info-compact {
        display: flex;
        flex-direction: column;
        gap: 10px;

        .connection-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 13px;

          .connection-label {
            color: #64748b;
          }

          .connection-value {
            font-weight: 600;
            color: #1e293b;

            &.connected {
              color: #10b981;
            }
          }
        }
      }
    }
  }

  // 右侧内容区: 任务列表 (flex: 1)
  .right-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;

    .toolbar-card-compact {
      border: none;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

      .toolbar-compact {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;

        .search-group-compact {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
          flex: 1;

          .search-input-compact {
            flex: 1;
            min-width: 200px;
            max-width: 300px;
          }
        }

        .toolbar-info {
          .task-count-info {
            font-size: 14px;
            color: #64748b;
            font-weight: 500;
          }
        }
      }
    }

    .task-list-card-compact {
      border: none;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
      flex: 1;

      .task-table-compact {
        :deep(.task-id) {
          font-family: 'Monaco', 'Menlo', monospace;
          font-size: 12px;
          color: #64748b;
          background: #f1f5f9;
          padding: 2px 6px;
          border-radius: 4px;
        }

        :deep(.task-info-cell) {
          .task-title {
            font-weight: 500;
            color: #1e293b;
            margin-bottom: 4px;
          }

          .task-desc {
            font-size: 12px;
            color: #94a3b8;
          }
        }

        :deep(.status-cell) {
          display: flex;
          align-items: center;
          gap: 8px;

          .status-tag-animated {
            animation: tagPulse 0.5s ease;
          }
        }

        :deep(.progress-cell) {
          display: flex;
          align-items: center;
          gap: 8px;

          .progress-text {
            font-size: 12px;
            font-weight: 500;
            color: #64748b;
            min-width: 36px;
          }

          :deep(.n-progress) {
            flex: 1;
          }
        }

        :deep(.current-step) {
          font-size: 12px;
          color: #64748b;
          max-width: 160px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          display: inline-block;
        }

        :deep(.action-buttons) {
          .n-button {
            transition: all 0.2s ease;
          }
        }

        :deep(.row-active) {
          background: rgba(102, 126, 234, 0.06);

          &:hover {
            background: rgba(102, 126, 234, 0.1);
          }
        }
      }

      .pagination-wrapper-compact {
        display: flex;
        justify-content: flex-end;
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid #e2e8f0;
      }
    }
  }
}

// 旧的 Agent 侧边栏样式 (保留以防需要)
.agent-sidebar {
  border: none;
  height: fit-content;
  position: sticky;
  top: 24px;

  .agent-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .agent-header-left {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      color: #1e293b;
    }
  }

  .agent-list {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .agent-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      background: #f8fafc;
      border-radius: 8px;
      transition: all 0.2s ease;

      &:hover {
        background: #f1f5f9;
        transform: translateX(4px);
      }

      &.offline {
        opacity: 0.6;
      }

      .agent-avatar {
        position: relative;

        .status-indicator-dot {
          position: absolute;
          bottom: 0;
          right: 0;
          width: 10px;
          height: 10px;
          border-radius: 50%;
          border: 2px solid #fff;

          &.idle {
            background: #10b981;
          }

          &.busy {
            background: var(--color-warning);
            animation: pulse 1.5s ease-in-out infinite;
          }

          &.offline {
            background: var(--color-text-tertiary);
          }
        }
      }

      .agent-info {
        flex: 1;
        min-width: 0;

        .agent-name {
          font-weight: 500;
          color: #1e293b;
          margin-bottom: 4px;
        }

        .agent-meta {
          display: flex;
          align-items: center;
          gap: 8px;

          .task-count-badge {
            font-size: 12px;
            color: var(--color-warning);
            font-weight: 500;
          }
        }
      }

      .capability-icon {
        color: #94a3b8;
        cursor: pointer;
        transition: color 0.2s ease;

        &:hover {
          color: var(--color-primary);
        }
      }
    }
  }

  .empty-agents {
    padding: 24px 0;
  }

  .capability-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    max-width: 200px;

    .capability-tag {
      font-size: 12px;
      padding: 2px 8px;
      background: #e0f2fe;
      color: #0369a1;
      border-radius: 4px;
    }
  }

  .connection-info {
    .connection-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 4px 0;

      .connection-label {
        font-size: 13px;
        color: #64748b;
      }

      .connection-value {
        font-size: 13px;
        font-weight: 500;
        color: #1e293b;
      }
    }
  }
}

// 结果 JSON 样式
.result-json {
  background: #1e293b;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
  font-family: 'Monaco', 'Menlo', monospace;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
}

// AI 对话流样式 - 重新设计（左右分栏布局）
.task-detail-content {
  display: flex;
  gap: 20px;
  align-items: flex-start;

  // 左栏：任务信息 + 进度
  .left-column {
    flex: 0 0 400px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  // 右栏：AI 对话流
  .right-column {
    flex: 1;
    min-width: 0; // 防止内容溢出
  }
}

// 任务详情对话框头部
.detail-header {
  padding: 0;

  .detail-title {
    display: flex;
    align-items: center;
    gap: 12px;

    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
      color: #1e293b;
    }
  }
}

// 信息卡片
.info-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 24px;
  color: white;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);

  .info-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;

    .task-title {
      font-size: 20px;
      font-weight: 600;
      line-height: 1.4;
      flex: 1;
    }

    .n-tag {
      background: rgba(255, 255, 255, 0.2);
      border: none;
      color: white;
    }
  }

  .info-card-body {
    .task-description {
      font-size: 14px;
      line-height: 1.6;
      margin-bottom: 16px;
      opacity: 0.95;
    }

    .task-meta {
      display: flex;
      gap: 24px;
      flex-wrap: wrap;

      .meta-item {
        display: flex;
        align-items: center;
        gap: 8px;

        .meta-label {
          font-size: 12px;
          opacity: 0.8;
        }

        .n-tag {
          background: rgba(255, 255, 255, 0.2);
          border: none;
        }
      }
    }
  }
}

// 进度卡片
.progress-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;

  .progress-header {
    margin-bottom: 20px;

    .progress-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;

      h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: #1e293b;
      }
    }

    .progress-bar-wrapper {
      :deep(.n-progress) {
        .n-progress-graph-line-fill {
          background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }
      }
    }
  }

  .time-info {
    display: flex;
    gap: 32px;
    padding-top: 16px;
    border-top: 1px solid #f1f5f9;

    .time-item {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .time-label {
        font-size: 12px;
        color: #64748b;
      }

      .time-value {
        font-size: 14px;
        color: #1e293b;
        font-weight: 500;
      }
    }
  }
}

// 对话流卡片（在 Tab 内部）
.conversation-card {
  .conversation-flow {
    // 固定高度并启用内部滚动
    max-height: 500px;
    overflow-y: auto;
    padding-right: 8px;

    // 美化滚动条
    &::-webkit-scrollbar {
      width: 8px;
    }

    &::-webkit-scrollbar-track {
      background: #f1f5f9;
      border-radius: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
      border-radius: 4px;

      &:hover {
        background: linear-gradient(180deg, #5a67d8 0%, #6b3fa0 100%);
      }
    }

    // Firefox 滚动条
    scrollbar-width: thin;
    scrollbar-color: #667eea #f1f5f9;

    .conversation-message {
      position: relative;
      margin-bottom: 20px;

      &:last-child {
        margin-bottom: 0;
      }

      .message-connector {
        position: absolute;
        left: 24px;
        top: -20px;
        width: 2px;
        height: 20px;
        background: linear-gradient(180deg, #667eea 0%, #e2e8f0 100%);
        z-index: 0;
      }

      .message-main {
        display: flex;
        gap: 12px;
        position: relative;
        z-index: 1;

        .message-icon {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;

          .icon-emoji {
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            flex-shrink: 0;
          }

          .icon-progress {
            padding: 4px 8px;
            background: white;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            color: #667eea;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
          }
        }

        .message-body {
          flex: 1;
          padding: 16px;
          background: #f8fafc;
          border-radius: 12px;
          border-left: 3px solid #667eea;
          transition: all 0.3s ease;

          .message-meta-line {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;

            .message-time {
              font-size: 12px;
              color: #94a3b8;
            }

            .n-tag {
              background: white;
              border: 1px solid #e2e8f0;
              font-weight: 500;
            }
          }

          .message-text {
            font-size: 14px;
            line-height: 1.7;
            color: #334155;
            white-space: pre-wrap;
            word-break: break-word;
          }
        }
      }

      &.is-complete {
        .message-icon {
          .icon-emoji {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
          }

          .icon-progress {
            color: #10b981;
          }
        }

        .message-body {
          border-left-color: #10b981;
          background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        }
      }

      &:hover {
        .message-main {
          .message-body {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            transform: translateY(-2px);
          }
        }
      }
    }
  }
}

// 评论卡片（在 Tab 内部）
.comments-card {
  .add-comment {
    margin-bottom: 24px;
    padding: 16px;
    background: #f8fafc;
    border-radius: 12px;
    border: 1px solid #e2e8f0;

    .comment-actions {
      margin-top: 12px;
      display: flex;
      justify-content: flex-end;
    }
  }

  .comments-list {
    display: flex;
    flex-direction: column;
    gap: 16px;

    .comment-item {
      padding: 16px;
      background: #f8fafc;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      transition: all 0.2s ease;

      &:hover {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border-color: #cbd5e1;
      }

      .comment-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }

      .comment-text {
        font-size: 14px;
        line-height: 1.6;
        color: #334155;
        white-space: pre-wrap;
        word-break: break-word;
      }
    }
  }
}

// 结果卡片
.result-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;

  .result-header {
    margin-bottom: 16px;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #1e293b;
    }
  }

  .result-content {
    .result-json {
      padding: 16px;
      background: #f8fafc;
      border-radius: 8px;
      font-size: 13px;
      line-height: 1.6;
      color: #334155;
      overflow-x: auto;
      border: 1px solid #e2e8f0;
    }
  }
}

// 错误卡片
.error-card {
  margin-top: 20px;
}

// 保留原有的 ai-conversation-flow 样式（向后兼容）
.ai-conversation-flow {
  max-height: 400px;
  overflow-y: auto;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;

  .conversation-message {
    margin-bottom: 16px;
    padding: 12px;
    background: white;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    transition: all 0.2s ease;

    &:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
      border-color: #cbd5e1;
    }

    .message-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;

      .message-avatar {
        font-size: 20px;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 50%;
      }

      .message-meta {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 2px;

        .message-agent {
          font-size: 13px;
          font-weight: 600;
          color: #1e293b;
        }

        .message-time {
          font-size: 11px;
          color: #94a3b8;
        }
      }

      .message-progress {
        margin-left: auto;
      }
    }

    .message-content {
      padding: 12px;
      background: #f1f5f9;
      border-radius: 8px;
      font-size: 14px;
      line-height: 1.6;
      color: #334155;
      margin-bottom: 8px;
      white-space: pre-wrap;
    }

    .message-step {
      display: flex;
      justify-content: flex-end;
    }
  }
}

// 动画
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.1);
  }
}

@keyframes tagPulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}

// 🎯 金币统计卡片样式
.coin-stats-card {
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .coin-stats-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .coin-stats-title {
      font-size: 15px;
      font-weight: 600;
      color: #1e293b;
    }
  }

  .coin-stats-content {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .coin-stat-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      border-radius: 10px;
      background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
      transition: all 0.2s ease;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(251, 191, 36, 0.3);
      }

      &.total {
        background: linear-gradient(135deg, #fbbf24 0%, var(--color-warning) 100%);
        color: white;
      }

      &.completed {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        color: #065f46;
      }

      &.pending {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        color: #1e40af;
      }

      &.rate {
        background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%);
        color: #9f1239;
      }

      .coin-stat-label {
        font-size: 13px;
        font-weight: 500;
        opacity: 0.9;
      }

      .coin-stat-value {
        font-size: 20px;
        font-weight: 700;
        margin: 0 8px;
      }

      .coin-stat-unit {
        font-size: 16px;
      }
    }

    .coin-stats-row {
      display: flex;
      gap: 8px;

      .coin-stat-item {
        flex: 1;
        padding: 10px 12px;

        .coin-stat-value {
          font-size: 18px;
        }

        .coin-stat-unit {
          font-size: 14px;
        }
      }
    }
  }
}

// 🎯 任务卡片网格样式（紧凑版）
.task-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 16px;

  .task-card {
    background: white;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    padding: 16px;
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
    gap: 12px;
    position: relative;
    overflow: hidden;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
      border-color: #667eea;
    }

    &.task-card-active {
      border-color: #667eea;
      box-shadow: 0 4px 16px rgba(102, 126, 234, 0.2);

      &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
      }
    }

    .task-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 10px;
      border-bottom: 1px solid #f1f5f9;

      .task-card-id {
        flex: 1;
        min-width: 0;
        margin-right: 8px;

        .task-id-text {
          font-size: 10px;
          color: #64748b;
          font-family: 'Monaco', 'Menlo', monospace;
          display: block;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          word-break: break-all;
        }
      }
    }

    .task-card-body {
      display: flex;
      flex-direction: column;
      gap: 10px;
      flex: 1;

      .task-card-title {
        margin: 0;
        font-size: 15px;
        font-weight: 600;
        color: #1e293b;
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      .task-card-description {
        margin: 0;
        font-size: 12px;
        color: #64748b;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      // 🎯 金币奖励和验收标准
      .task-card-rewards {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;

        .task-reward-badge,
        .task-criteria-badge {
          display: inline-flex;
          align-items: center;
          gap: 3px;
          padding: 3px 8px;
          border-radius: 10px;
          font-size: 11px;
          font-weight: 500;
        }

        .task-reward-badge {
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          color: #92400e;

          .reward-icon {
            font-size: 13px;
          }

          .reward-value {
            font-weight: 600;
          }
        }

        .task-criteria-badge {
          background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
          color: #065f06;

          .criteria-icon {
            font-size: 11px;
            font-weight: 700;
          }

          .criteria-count {
            font-weight: 500;
          }
        }
      }

      .task-card-progress-simple {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;

        .progress-percent {
          color: #667eea;
          font-weight: 600;
          font-size: 12px;
          flex-shrink: 0;
        }

        .progress-status {
          color: #64748b;
          font-weight: 400;
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .progress-time {
          color: #94a3b8;
          font-size: 9px;
          font-weight: 400;
          flex-shrink: 0;
          margin-left: auto;
        }
      }
    }

    .task-card-actions {
      display: flex;
      gap: 6px;
      padding-top: 10px;
      border-top: 1px solid #f1f5f9;

      button {
        flex: 1;
      }
    }
  }
}

// 响应式
@media (max-width: 768px) {
  .task-management {
    padding: 16px;

    .page-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;

      .header-left {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
      }
    }

    // 🎯 卡片响应式
    .task-cards-grid {
      grid-template-columns: 1fr;
      gap: 16px;
    }

    .stats-section {
      .stat-card {
        .stat-content {
          .stat-icon {
            width: 40px;
            height: 40px;
          }

          .stat-info .stat-value {
            font-size: 24px;
          }
        }
      }
    }

    .main-content {
      .toolbar-card .toolbar {
        flex-direction: column;
        align-items: stretch;

        .search-group {
          .search-input {
            width: 100%;
          }
        }
      }
    }

    .agent-sidebar {
      position: static;
    }
  }
}
</style>
