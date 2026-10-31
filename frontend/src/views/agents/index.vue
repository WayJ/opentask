<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import {
  NAlert,
  NAvatar,
  NButton,
  NCard,
  NDrawer,
  NDrawerContent,
  NProgress,
  NSelect,
  NSpace,
  NStatistic,
  NTabPane,
  NTabs,
  useMessage
} from 'naive-ui';
import { type Agent, fetchAgentStats, fetchAgents, reactivateAgent, retireAgent } from '@/service/api/agent';

const message = useMessage();

// 状态
const loading = ref(false);
const agents = ref<Agent[]>([]);
const showDrawer = ref(false);
const selectedAgent = ref<Agent>({} as Agent);

const stats = ref({
  total_agents: 0,
  online_agents: 0,
  offline_agents: 0,
  retired_agents: 0,
  active_agents: 0,
  total_tasks: 0,
  successful_tasks: 0,
  failed_tasks: 0,
  success_rate: 0
});

const filters = reactive({
  status: null,
  agent_type: null,
  is_active: null
});

const pagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0
});

// 选项
const statusOptions = [
  { label: '在线', value: 'online' },
  { label: '空闲', value: 'idle' },
  { label: '忙碌', value: 'busy' },
  { label: '离线', value: 'offline' },
  { label: '已退役', value: 'retired' }
];

const typeOptions = [
  { label: '架构师', value: 'architecture' },
  { label: '娱乐', value: 'entertainment' },
  { label: '编程', value: 'coding' }
];

const activeOptions = [
  { label: '激活', value: true },
  { label: '未激活', value: false }
];

// 表格列
const columns = [
  { title: 'Agent ID', key: 'agent_id', width: 200 },
  { title: '名称', key: 'agent_name', width: 150 },
  {
    title: '类型',
    key: 'agent_type',
    width: 100,
    render: (row: Agent) => h(NTag, { type: 'info' }, () => row.agent_type)
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: Agent) => h(NTag, { type: getStatusColor(row.status) }, () => getStatusLabel(row.status))
  },
  { title: '处理任务', key: 'total_tasks_handled', width: 100 },
  { title: '成功', key: 'successful_tasks', width: 80 },
  { title: '失败', key: 'failed_tasks', width: 80 },
  {
    title: '最后心跳',
    key: 'last_heartbeat',
    width: 180,
    render: (row: Agent) => formatTime(row.last_heartbeat)
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render: (row: Agent) => h(NButton, { onClick: () => viewDetails(row) }, () => '详情')
  }
];

// 方法
async function loadAgents() {
  loading.value = true;
  try {
    const data = await fetchAgents({
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      agent_type: filters.agent_type as any,
      status: filters.status as any,
      is_active: filters.is_active
    });

    agents.value = data.data || [];
    pagination.itemCount = data.data?.length || 0;
  } catch (error) {
    message.error('加载 Agent 列表失败');
    console.error('Failed to fetch agents:', error);
  } finally {
    loading.value = false;
  }
}

async function loadStats() {
  try {
    const data = await fetchAgentStats();
    stats.value = data.data;
  } catch (error) {
    console.error('Failed to fetch stats:', error);
  }
}

function refreshAgents() {
  pagination.page = 1;
  loadAgents();
  loadStats();
}

function handlePageChange(page: number) {
  pagination.page = page;
  loadAgents();
}

function viewDetails(agent: Agent) {
  selectedAgent.value = agent;
  showDrawer.value = true;
}

async function handleRetireAgent() {
  // eslint-disable-next-line no-alert
  const reason = prompt('请输入退役原因：');
  if (!reason) return;

  try {
    await retireAgent(selectedAgent.value.agent_id, 'admin', reason);
    message.success('Agent 已退役');
    showDrawer.value = false;
    refreshAgents();
  } catch (error) {
    message.error('退役失败');
    console.error('Failed to retire agent:', error);
  }
}

async function handleReactivateAgent() {
  try {
    await reactivateAgent(selectedAgent.value.agent_id);
    message.success('Agent 已重新激活');
    showDrawer.value = false;
    refreshAgents();
  } catch (error) {
    message.error('重新激活失败');
    console.error('Failed to reactivate agent:', error);
  }
}

// 辅助函数
function getStatusColor(status: string): 'default' | 'info' | 'success' | 'warning' | 'error' {
  const colors: Record<string, any> = {
    online: 'success',
    idle: 'info',
    busy: 'warning',
    offline: 'error',
    retired: 'default',
    registered: 'default'
  };
  return colors[status] || 'default';
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    online: '在线',
    idle: '空闲',
    busy: '忙碌',
    offline: '离线',
    retired: '已退役',
    registered: '已注册'
  };
  return labels[status] || status;
}

function getAgentIcon(type: string): string {
  const icons: Record<string, string> = {
    architecture: '🏗️',
    entertainment: '🎭',
    coding: '💻'
  };
  return icons[type] || '🤖';
}

function getAvatarColor(type: string): string {
  const colors: Record<string, string> = {
    architecture: '#18a058',
    entertainment: '#f0a020',
    coding: '#2080f0'
  };
  return colors[type] || '#606266';
}

function getSuccessRate(agent: Agent): number {
  if (agent.total_tasks_handled === 0) return 0;
  return Math.round((agent.successful_tasks / agent.total_tasks_handled) * 100);
}

function getSuccessRateColor(rate: number): string {
  if (rate >= 90) return '#18a058';
  if (rate >= 70) return '#f0a020';
  return '#d03050';
}

function formatTime(time: string | null): string {
  if (!time) return 'N/A';
  return new Date(time).toLocaleString('zh-CN');
}

// 初始化
onMounted(() => {
  loadAgents();
  loadStats();
});
</script>

<template>
  <div class="agents-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>Agent 管理</h1>
      <NSpace>
        <NButton type="primary" @click="refreshAgents">刷新</NButton>
      </NSpace>
    </div>

    <!-- 统计卡片 -->
    <NGrid :cols="4" :x-gap="16" class="stats-grid">
      <NGridItem>
        <NCard>
          <NStatistic label="总 Agent 数" :value="stats.total_agents" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard>
          <NStatistic label="在线 Agent" :value="stats.online_agents">
            <template #suffix>/ {{ stats.total_agents }}</template>
          </NStatistic>
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard>
          <NStatistic label="已完成任务" :value="stats.successful_tasks" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard>
          <NStatistic label="成功率" :value="stats.success_rate" suffix="%" />
        </NCard>
      </NGridItem>
    </NGrid>

    <!-- 过滤器 -->
    <NCard class="filter-card">
      <NSpace align="center" :size="12">
        <span>筛选：</span>
        <NSelect
          v-model:value="filters.status"
          :options="statusOptions"
          placeholder="全部状态"
          clearable
          style="width: 150px"
          @update:value="refreshAgents"
        />
        <NSelect
          v-model:value="filters.agent_type"
          :options="typeOptions"
          placeholder="全部类型"
          clearable
          style="width: 150px"
          @update:value="refreshAgents"
        />
        <NSelect
          v-model:value="filters.is_active"
          :options="activeOptions"
          placeholder="激活状态"
          clearable
          style="width: 150px"
          @update:value="refreshAgents"
        />
      </NSpace>
    </NCard>

    <!-- Agent 列表 -->
    <NCard>
      <NDataTable
        :columns="columns"
        :data="agents"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.agent_id"
        @update:page="handlePageChange"
      />
    </NCard>

    <!-- Agent 详情抽屉 -->
    <NDrawer v-model:show="showDrawer" :width="800">
      <NDrawerContent>
        <template #header>
          <NSpace align="center">
            <NAvatar :style="{ backgroundColor: getAvatarColor(selectedAgent.agent_type) }" :size="64">
              {{ getAgentIcon(selectedAgent.agent_type) }}
            </NAvatar>
            <div>
              <h2>{{ selectedAgent.agent_name }}</h2>
              <NSpace align="center" :size="8">
                <NTag :type="getStatusColor(selectedAgent.status)">
                  {{ getStatusLabel(selectedAgent.status) }}
                </NTag>
                <NTag type="info">{{ selectedAgent.agent_type }}</NTag>
                <NTag v-if="!selectedAgent.is_active" type="warning">已退役</NTag>
              </NSpace>
            </div>
          </NSpace>
        </template>

        <!-- Agent 详情内容 -->
        <NTabs>
          <NTabPane name="overview" tab="概览">
            <NDescriptions bordered :column="2">
              <NDescriptionsItem label="Agent ID">
                {{ selectedAgent.agent_id }}
              </NDescriptionsItem>
              <NDescriptionsItem label="显示名称">
                {{ selectedAgent.agent_name }}
              </NDescriptionsItem>
              <NDescriptionsItem label="Agent 类型">
                {{ selectedAgent.agent_type }}
              </NDescriptionsItem>
              <NDescriptionsItem label="AI 模型">
                {{ selectedAgent.model || 'N/A' }}
              </NDescriptionsItem>
              <NDescriptionsItem label="当前状态">
                <NTag :type="getStatusColor(selectedAgent.status)">
                  {{ getStatusLabel(selectedAgent.status) }}
                </NTag>
              </NDescriptionsItem>
              <NDescriptionsItem label="是否激活">
                <NTag :type="selectedAgent.is_active ? 'success' : 'warning'">
                  {{ selectedAgent.is_active ? '是' : '否' }}
                </NTag>
              </NDescriptionsItem>
              <NDescriptionsItem label="首次连接">
                {{ formatTime(selectedAgent.connected_at) }}
              </NDescriptionsItem>
              <NDescriptionsItem label="最后心跳">
                {{ formatTime(selectedAgent.last_heartbeat) }}
              </NDescriptionsItem>
            </NDescriptions>

            <NDivider>能力列表</NDivider>
            <NSpace v-if="selectedAgent.capabilities && selectedAgent.capabilities.length">
              <NTag v-for="capability in selectedAgent.capabilities" :key="capability" type="info">
                {{ capability }}
              </NTag>
            </NSpace>
            <NText v-else depth="3">无能力信息</NText>
          </NTabPane>

          <NTabPane name="stats" tab="统计">
            <NDescriptions bordered :column="2">
              <NDescriptionsItem label="总任务数">
                {{ selectedAgent.total_tasks_handled }}
              </NDescriptionsItem>
              <NDescriptionsItem label="成功任务">
                <NText type="success">{{ selectedAgent.successful_tasks }}</NText>
              </NDescriptionsItem>
              <NDescriptionsItem label="失败任务">
                <NText type="error">{{ selectedAgent.failed_tasks }}</NText>
              </NDescriptionsItem>
              <NDescriptionsItem label="总执行时间">{{ selectedAgent.total_execution_time }} 秒</NDescriptionsItem>
              <NDescriptionsItem label="成功率">
                <NProgress
                  type="line"
                  :percentage="getSuccessRate(selectedAgent)"
                  :color="getSuccessRateColor(getSuccessRate(selectedAgent))"
                />
              </NDescriptionsItem>
            </NDescriptions>

            <NDivider>健康监控</NDivider>
            <NDescriptions bordered :column="2">
              <NDescriptionsItem label="心跳丢失次数">
                <NText :type="selectedAgent.heartbeat_misses > 0 ? 'warning' : 'default'">
                  {{ selectedAgent.heartbeat_misses }}
                </NText>
              </NDescriptionsItem>
              <NDescriptionsItem label="错误次数">
                <NText :type="selectedAgent.error_count > 0 ? 'error' : 'default'">
                  {{ selectedAgent.error_count }}
                </NText>
              </NDescriptionsItem>
              <NDescriptionsItem label="最后错误" span="2">
                <NText v-if="selectedAgent.last_error" type="error" code>
                  {{ selectedAgent.last_error }}
                </NText>
                <NText v-else depth="3">无错误</NText>
              </NDescriptionsItem>
            </NDescriptions>

            <NDivider v-if="selectedAgent.current_task_id">当前任务</NDivider>
            <NCard v-if="selectedAgent.current_task_id" size="small">
              <p>
                <strong>任务 ID:</strong>
                {{ selectedAgent.current_task_id }}
              </p>
              <p>
                <strong>开始时间:</strong>
                {{ formatTime(selectedAgent.current_task_started_at) }}
              </p>
            </NCard>
          </NTabPane>

          <NTabPane name="actions" tab="操作">
            <NSpace vertical>
              <NAlert v-if="!selectedAgent.is_active" type="warning" title="Agent 已退役">
                {{ selectedAgent.retire_reason || '无原因' }}
                <br />
                退役时间: {{ formatTime(selectedAgent.retired_at) }}
                <br />
                操作者: {{ selectedAgent.retired_by }}
              </NAlert>

              <NCard v-if="selectedAgent.current_task_id" title="警告">
                <p>此 Agent 正在处理任务，无法退役</p>
                <p>
                  <strong>当前任务:</strong>
                  {{ selectedAgent.current_task_id }}
                </p>
              </NCard>

              <NButton
                v-if="selectedAgent.is_active && !selectedAgent.current_task_id"
                type="warning"
                @click="handleRetireAgent"
              >
                退役此 Agent
              </NButton>

              <NButton v-if="!selectedAgent.is_active" type="success" @click="handleReactivateAgent">
                重新激活 Agent
              </NButton>
            </NSpace>
          </NTabPane>
        </NTabs>
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<style scoped>
.agents-page {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.stats-grid {
  margin-bottom: 24px;
}

.filter-card {
  margin-bottom: 16px;
}
</style>
