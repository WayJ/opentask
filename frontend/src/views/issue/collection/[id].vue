<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NAlert,
  NBadge,
  NButton,
  NCard,
  NDivider,
  NEmpty,
  NIcon,
  NInput,
  NModal,
  NProgress,
  NSpace,
  NSpin,
  NTag,
  NText,
  NTooltip
} from 'naive-ui';
import MarkdownIt from 'markdown-it';
import { issueApi, issueCollectionApi } from '@/service/api';
import MarkdownEditor from '@/components/MarkdownEditor.vue';
import AgentPromptModal from '@/components/AgentPromptModal.vue';

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true // 启用换行符转换，单个换行符会转换为<br>
});

defineOptions({
  name: 'IssueCollectionDetail'
});

const router = useRouter();
const route = useRoute();

const collection = ref<any | null>(null);
const loading = ref(false);
const editing = ref(false);
const editingDescription = ref(false);
const editTitle = ref('');
const editDescription = ref('');

// 关联的 Issues
const relatedIssues = ref<any[]>([]);
const issuesLoading = ref(false);

// 是否显示侧边栏
const showSidebar = ref(true);

// 是否显示 API 弹窗
const showApiModal = ref(false);

// 是否显示 Agent 指令弹窗
const showAgentPromptModal = ref(false);

// 计算属性
const statistics = computed(() => collection.value?.statistics);
const completionPercentage = computed(() => {
  if (!statistics.value || statistics.value.total === 0) return 0;
  return Math.round(statistics.value.completion_rate * 100);
});

const completionColor = computed(() => {
  const pct = completionPercentage.value;
  if (pct >= 80) return '#52c41a';
  if (pct >= 50) return '#faad14';
  return '#ff4d4f';
});

const completionStatus = computed(() => {
  const pct = completionPercentage.value;
  if (pct === 100) return { text: '全部完成', emoji: '✅' };
  if (pct >= 80) return { text: '进展良好', emoji: '📈' };
  if (pct >= 50) return { text: '进行中', emoji: '🔄' };
  if (pct > 0) return { text: '刚开始', emoji: '▶️' };
  return { text: '未开始', emoji: '⏸️' };
});

// 渲染后的Markdown HTML
const renderedDescription = computed(() => {
  if (!collection.value?.description) return '';
  return md.render(collection.value.description);
});

// 加载问题集详情
async function loadCollection() {
  loading.value = true;
  try {
    const response = await issueCollectionApi.getCollection(route.params.id as string);
    if (response.data) {
      collection.value = response.data;
      editTitle.value = response.data.title;
      editDescription.value = response.data.description || '';

      // 加载关联的 Issues
      if (response.data.issue_ids && response.data.issue_ids.length > 0) {
        await loadRelatedIssues(response.data.issue_ids);
      }
    }
  } catch {
    window.$message?.error('加载失败');
    router.back();
  } finally {
    loading.value = false;
  }
}

// 加载关联的 Issues（使用批量查询接口优化性能）
async function loadRelatedIssues(issueIds: string[]) {
  if (!issueIds || issueIds.length === 0) {
    relatedIssues.value = [];
    return;
  }

  issuesLoading.value = true;
  try {
    // 使用批量查询接口，一次调用获取所有 issues
    const response = await issueApi.getIssuesByIds(issueIds);
    relatedIssues.value = response.data?.rows || [];
  } catch (err) {
    console.error('加载关联 Issues 失败:', err);
    window.$message?.error('加载关联 Issues 失败');
    relatedIssues.value = [];
  } finally {
    issuesLoading.value = false;
  }
}

// 保存编辑
async function saveEdit() {
  if (!collection.value) return;

  try {
    await issueCollectionApi.updateCollection(collection.value.id, {
      title: editTitle.value,
      description: editDescription.value
    });
    window.$message?.success('保存成功');
    editing.value = false;
    editingDescription.value = false;
    await loadCollection();
  } catch {
    window.$message?.error('保存失败');
  }
}

// 取消编辑
function cancelEdit() {
  if (collection.value) {
    editTitle.value = collection.value.title;
    editDescription.value = collection.value.description || '';
  }
  editing.value = false;
  editingDescription.value = false;
}

// 开始编辑
function startEdit() {
  editing.value = true;
  editingDescription.value = true;
}

// 取消描述编辑
function cancelDescriptionEdit() {
  if (collection.value) {
    editDescription.value = collection.value.description || '';
  }
  editingDescription.value = false;
}

// 保存描述编辑
async function saveDescriptionEdit() {
  if (!collection.value) return;

  try {
    await issueCollectionApi.updateCollection(collection.value.id, {
      description: editDescription.value
    });
    window.$message?.success('保存成功');
    editingDescription.value = false;
    await loadCollection();
  } catch {
    window.$message?.error('保存失败');
  }
}

// 删除问题集
// eslint-disable-next-line @typescript-eslint/no-unused-vars
async function handleDelete() {
  if (!collection.value) return;

  try {
    await issueCollectionApi.deleteCollection(collection.value.id);
    window.$message?.success('删除成功');
    router.push('/issue/collection-list');
  } catch {
    window.$message?.error('删除失败');
  }
}

// 调用解析 API
async function callParseAPI() {
  window.$message?.info('此功能由外部 AI 服务调用');
}

// 跳转到 Issue 详情
function goToIssue(issueId: string) {
  router.push(`/issue/detail?id=${issueId}`);
}

// 状态标签类型
function getStatusTagType(status: string) {
  const typeMap: Record<string, any> = {
    open: 'default',
    in_progress: 'warning',
    feedback: 'info',
    resolved: 'success',
    closed: 'default',
    rejected: 'error'
  };
  return typeMap[status] || 'default';
}

function getStatusText(status: string) {
  const textMap: Record<string, string> = {
    open: '待处理',
    in_progress: '进行中',
    feedback: '等待反馈',
    resolved: '已解决',
    closed: '已关闭',
    rejected: '已拒绝'
  };
  return textMap[status] || status;
}

function getStatusEmoji(status: string) {
  const emojiMap: Record<string, string> = {
    open: '⏳',
    in_progress: '🔄',
    feedback: '💬',
    resolved: '✅',
    closed: '🔒',
    rejected: '❌'
  };
  return emojiMap[status] || '⏳';
}

onMounted(() => {
  loadCollection();
});
</script>

<template>
  <div class="collection-detail-container h-full overflow-hidden">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <NSpin size="large" />
    </div>

    <!-- 主内容 -->
    <div v-else-if="collection" class="main-content">
      <!-- 顶部导航栏 -->
      <div class="top-navbar">
        <div class="navbar-content">
          <!-- 左侧 -->
          <div class="navbar-left">
            <NTooltip trigger="hover">
              <template #trigger>
                <NButton text @click="router.back()">
                  <NIcon size="24"><icon-mdi-arrow-left /></NIcon>
                </NButton>
              </template>
              返回列表
            </NTooltip>

            <div v-if="!editing" class="title-section">
              <h1 class="page-title">
                {{ collection.title }}
              </h1>
              <NText depth="3" class="page-subtitle">{{ collection.issue_ids?.length || 0 }} 个关联问题</NText>
            </div>

            <NInput v-else v-model:value="editTitle" size="large" class="edit-title-input" />
          </div>

          <!-- 右侧 -->
          <div class="navbar-right">
            <NSpace :size="8">
              <NTooltip v-if="!editing" trigger="hover">
                <template #trigger>
                  <NButton type="primary" @click="startEdit">
                    <NIcon class="mr-1" size="18"><icon-mdi-pencil /></NIcon>
                    编辑
                  </NButton>
                </template>
                编辑问题集
              </NTooltip>

              <template v-else>
                <NButton size="small" @click="cancelEdit">取消</NButton>
                <NButton size="small" type="primary" @click="saveEdit">保存</NButton>
              </template>

              <NTooltip trigger="hover">
                <template #trigger>
                  <NButton text @click="showSidebar = !showSidebar">
                    <NIcon size="20">
                      <icon-mdi-menu v-if="!showSidebar" />
                      <icon-mdi-menu-open v-else />
                    </NIcon>
                  </NButton>
                </template>
                {{ showSidebar ? '隐藏' : '显示' }}侧边栏
              </NTooltip>
            </NSpace>
          </div>
        </div>
      </div>

      <!-- 内容区域 -->
      <div class="content-body">
        <!-- 主内容区 -->
        <div class="content-area" :class="{ 'with-sidebar': showSidebar }">
          <!-- 元信息卡片 -->
          <NCard class="meta-card" size="small">
            <div class="meta-grid">
              <div class="meta-item">
                <div class="meta-icon">👤</div>
                <div class="meta-info">
                  <div class="meta-label">创建者</div>
                  <div class="meta-value">
                    {{ collection.creator?.sso_name || collection.creator?.name || collection.creator_id }}
                  </div>
                </div>
              </div>

              <div class="meta-item">
                <div class="meta-icon">📅</div>
                <div class="meta-info">
                  <div class="meta-label">创建时间</div>
                  <div class="meta-value">{{ new Date(collection.created_at).toLocaleDateString('zh-CN') }}</div>
                </div>
              </div>

              <div class="meta-item">
                <div class="meta-icon">🕒</div>
                <div class="meta-info">
                  <div class="meta-label">最后更新</div>
                  <div class="meta-value">{{ new Date(collection.updated_at).toLocaleDateString('zh-CN') }}</div>
                </div>
              </div>

              <!--
 <div class="meta-item">
                <div class="meta-icon">🆔</div>
                <div class="meta-info">
                  <div class="meta-label">ID</div>
                  <div class="meta-value id-code">{{ collection.id.slice(0, 8) }}</div>
                </div>
              </div> 
-->
            </div>
          </NCard>

          <!-- 描述内容 -->
          <NCard class="description-card" size="small">
            <template #header>
              <div class="card-header-with-action">
                <div class="card-header">
                  <span class="card-icon">📝</span>
                  <span>问题描述</span>
                </div>
                <!-- 全局编辑模式下显示全局保存/取消 -->
                <template v-if="editing">
                  <NButton size="small" @click="cancelEdit">取消</NButton>
                  <NButton size="small" type="primary" class="ml-2" @click="saveEdit">保存</NButton>
                </template>
                <!-- 仅描述编辑模式 -->
                <template v-else-if="editingDescription">
                  <NButton size="small" @click="cancelDescriptionEdit">取消</NButton>
                  <NButton size="small" type="primary" class="ml-2" @click="saveDescriptionEdit">保存</NButton>
                </template>
                <!-- 非编辑模式显示编辑按钮 -->
                <NButton v-else text size="small" type="primary" @click="editingDescription = true">
                  <NIcon size="14" class="mr-1"><icon-mdi-pencil /></NIcon>
                  编辑
                </NButton>
              </div>
            </template>

            <div v-if="!editing && !editingDescription" class="markdown-content">
              <div v-if="renderedDescription" class="markdown-body" v-html="renderedDescription" />
              <NEmpty v-else description="暂无描述" size="small" />
            </div>

            <MarkdownEditor
              v-else
              v-model="editDescription"
              placeholder="请输入问题描述（支持 Markdown 格式）..."
              :rows="12"
            />
          </NCard>

          <!-- 关联的 Issue 列表 -->
          <NCard class="issues-card" size="small">
            <template #header>
              <div class="card-header">
                <span class="card-icon">🔗</span>
                <span>关联的 Issue</span>
                <NBadge :value="relatedIssues.length" :max="99" type="info" />
              </div>
            </template>

            <NSpin :show="issuesLoading">
              <div v-if="relatedIssues.length > 0" class="issues-list">
                <div v-for="issue in relatedIssues" :key="issue.id" class="issue-item" @click="goToIssue(issue.id)">
                  <div class="issue-left">
                    <div class="issue-emoji">{{ getStatusEmoji(issue.status) }}</div>
                    <div class="issue-info">
                      <div class="issue-code">{{ issue.issue_code }}</div>
                      <div class="issue-title">{{ issue.title }}</div>
                    </div>
                  </div>

                  <div class="issue-right">
                    <NTag :type="getStatusTagType(issue.status)" size="small" :bordered="false">
                      {{ getStatusText(issue.status) }}
                    </NTag>
                  </div>
                </div>
              </div>

              <NEmpty v-else description="暂无关联的 Issue" size="small">
                <template #extra>
                  <NText depth="3" style="font-size: 12px">点击"调用拆解 API"可由AI服务自动生成Issue</NText>
                </template>
              </NEmpty>
            </NSpin>
          </NCard>
        </div>

        <!-- 侧边栏 -->
        <div v-if="showSidebar" class="sidebar">
          <!-- 完成率卡片 -->
          <NCard class="completion-card" size="small">
            <template #header>
              <div class="card-header">
                <span class="card-icon">📊</span>
                <span>完成进度</span>
              </div>
            </template>

            <div class="completion-content">
              <!-- 环形进度条 -->
              <div class="progress-circle">
                <NProgress
                  type="circle"
                  :percentage="completionPercentage"
                  :stroke-width="12"
                  :color="completionColor"
                  rail-color="#f0f0f0"
                >
                  <div class="progress-text">
                    <div class="progress-emoji">{{ completionStatus.emoji }}</div>
                    <div class="progress-percentage">{{ completionPercentage }}%</div>
                    <div class="progress-status" :style="{ color: completionColor }">
                      {{ completionStatus.text }}
                    </div>
                  </div>
                </NProgress>
              </div>

              <!-- 统计数字 -->
              <div v-if="statistics" class="statistics-grid">
                <div class="stat-item">
                  <div class="stat-label">总计</div>
                  <div class="stat-value total">{{ statistics.total }}</div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">已完成</div>
                  <div class="stat-value success">{{ statistics.completed }}</div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">进行中</div>
                  <div class="stat-value warning">{{ statistics.in_progress }}</div>
                </div>
                <div class="stat-item">
                  <div class="stat-label">待处理</div>
                  <div class="stat-value pending">{{ statistics.pending }}</div>
                </div>
              </div>
            </div>
          </NCard>

          <!-- 快速操作卡片 -->
          <NCard class="actions-card" size="small">
            <template #header>
              <div class="card-header">
                <span class="card-icon">⚡</span>
                <span>快速操作</span>
              </div>
            </template>

            <NSpace vertical :size="8">
              <!--
 <NButton block secondary type="info" @click="showApiModal = true">
                <span class="action-icon">🤖</span>
                调用拆解 API
              </NButton> 
-->

              <NButton block secondary type="info" @click="showAgentPromptModal = true">
                <span class="action-icon">📋</span>
                获取 Agent 指令
              </NButton>

              <NButton block secondary @click="loadCollection">
                <span class="action-icon">🔄</span>
                刷新数据
              </NButton>

              <NDivider />

              <!--
 <NPopconfirm @positive-click="handleDelete">
                <template #trigger>
                  <NButton block secondary type="error">
                    <span class="action-icon">🗑️</span>
                    删除问题集
                  </NButton>
                </template>
                确定要删除这个问题集吗？此操作不可恢复。
              </NPopconfirm> 
-->
            </NSpace>
          </NCard>

          <!-- API 说明卡片 -->
          <NCard class="api-card" size="small">
            <template #header>
              <div class="card-header">
                <span class="card-icon">📡</span>
                <span>API 说明</span>
              </div>
            </template>

            <NAlert type="info" size="small">
              外部 AI 服务可调用此 API 拆解问题集：
              <div class="api-endpoint">POST /api/issues/collections/{{ collection.id.slice(0, 8) }}/parse</div>
            </NAlert>
          </NCard>
        </div>
      </div>
    </div>

    <!-- API 弹窗 -->
    <NModal v-model:show="showApiModal" preset="card" title="调用拆解 API" class="api-modal">
      <NAlert type="info" class="mb-4">此 API 供外部 AI 服务调用，将问题集拆解为具体的 Issue。</NAlert>

      <div class="api-info">
        <div class="api-section">
          <NText strong>API 端点：</NText>
          <div class="api-code">POST /api/issues/collections/{{ collection?.id }}/parse</div>
        </div>

        <NDivider />

        <div class="api-section">
          <NText strong>请求示例：</NText>
          <div class="api-code">
            <pre>{{
              JSON.stringify(
                {
                  issues: [
                    {
                      title: '登录页面加载慢',
                      description: '详细描述...',
                      type: 'bug',
                      priority: 'high'
                    }
                  ]
                },
                null,
                2
              )
            }}</pre>
          </div>
        </div>

        <NDivider />

        <NButton type="primary" block @click="callParseAPI">测试调用（仅示例）</NButton>
      </div>
    </NModal>

    <!-- Agent 指令弹窗组件 -->
    <AgentPromptModal
      v-model:show="showAgentPromptModal"
      :collection-title="collection?.title || ''"
      :collection-id="collection?.id || ''"
      :issues="relatedIssues"
    />
  </div>
</template>

<style scoped>
.collection-detail-container {
  position: relative;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* 背景装饰 */
.bg-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.circle {
  position: absolute;
  border-radius: 50%;
  opacity: 0.1;
  animation: float 20s infinite ease-in-out;
}

.circle-1 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  top: -100px;
  right: -50px;
  animation-delay: 0s;
}

.circle-2 {
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  bottom: -50px;
  left: -30px;
  animation-delay: 5s;
}

.circle-3 {
  width: 150px;
  height: 150px;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  top: 50%;
  left: 10%;
  animation-delay: 10s;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(180deg);
  }
}

/* 加载容器 */
.loading-container {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 主内容 */
.main-content {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 顶部导航栏 */
.top-navbar {
  background: white;
  border-bottom: 1px solid var(--color-border-subtle);
  padding: 16px 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.navbar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 100%;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.title-section {
  flex: 1;
  min-width: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(135deg, #2080f0 0%, #18a058 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-subtitle {
  font-size: 13px;
  margin-top: 2px;
}

.edit-title-input {
  max-width: 500px;
}

.navbar-right {
  flex-shrink: 0;
}

/* 内容区 */
.content-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  transition: all 0.3s ease;
}

.content-area.with-sidebar {
  margin-right: 360px;
}

/* 卡片通用样式 */
.meta-card,
.description-card,
.issues-card {
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border-radius: 16px;
  border: 1px solid var(--color-border-subtle);
}

.meta-card :deep(.n-card__content),
.description-card :deep(.n-card__content) {
  padding: 20px;
}

.issues-card :deep(.n-card__content) {
  padding-left: 20px;
  padding-right: 20px;
  padding-top: 8px;
  padding-bottom: 20px;
}

/* 元信息网格 */
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.meta-item:hover {
  background: #f3f4f6;
  transform: translateY(-2px);
}

.meta-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.meta-info {
  flex: 1;
  min-width: 0;
}

.meta-label {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-bottom: 2px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.meta-value {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.id-code {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  background: var(--color-border-subtle);
  padding: 2px 6px;
  border-radius: 4px;
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
}

.card-icon {
  font-size: 18px;
}

/* 描述内容 */
.markdown-content {
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
}

.markdown-body {
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
}

/* Markdown 样式 */
.markdown-body :deep(h1) {
  font-size: 2em;
  font-weight: 700;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  color: #1f2937;
  border-bottom: 2px solid var(--color-border-subtle);
  padding-bottom: 0.3em;
}

.markdown-body :deep(h2) {
  font-size: 1.5em;
  font-weight: 600;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  color: #1f2937;
  border-bottom: 1px solid var(--color-border-subtle);
  padding-bottom: 0.3em;
}

.markdown-body :deep(h3) {
  font-size: 1.25em;
  font-weight: 600;
  margin-top: 1.2em;
  margin-bottom: 0.4em;
  color: #374151;
}

.markdown-body :deep(p) {
  margin-top: 0;
  margin-bottom: 1em;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-top: 0;
  margin-bottom: 1em;
  padding-left: 2em;
}

.markdown-body :deep(li) {
  margin-bottom: 0.25em;
}

.markdown-body :deep(code) {
  background: #f3f4f6;
  color: #e11d48;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9em;
}

.markdown-body :deep(pre) {
  background: #1f2937;
  color: var(--color-border-subtle);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1em 0;
}

.markdown-body :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
  font-size: 0.9em;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid var(--color-primary);
  padding-left: 1em;
  margin: 1em 0;
  color: var(--color-text-secondary);
  font-style: italic;
}

.markdown-body :deep(a) {
  color: var(--color-primary);
  text-decoration: none;
  transition: color 0.2s;
}

.markdown-body :deep(a:hover) {
  color: var(--color-primary-hover);
  text-decoration: underline;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--color-border-subtle);
  padding: 8px 12px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f9fafb;
  font-weight: 600;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 2px solid var(--color-border-subtle);
  margin: 2em 0;
}

.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 1em 0;
}

/* Issue 列表 - 适度紧凑样式 */
.issues-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: white;
  border: 1px solid var(--color-border-subtle);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.issue-item:hover {
  background: #f9fafb;
  border-color: var(--color-border-default);
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.issue-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.issue-emoji {
  font-size: 18px;
  flex-shrink: 0;
  line-height: 1;
}

.issue-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.issue-code {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-weight: 500;
  line-height: 1.2;
}

.issue-title {
  font-size: 13px;
  font-weight: 500;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}

.issue-right {
  flex-shrink: 0;
  margin-left: 10px;
}

/* 侧边栏 */
.sidebar {
  position: fixed;
  right: 0;
  top: 73px;
  width: 360px;
  height: calc(100vh - 73px);
  overflow-y: auto;
  background: white;
  border-left: 1px solid var(--color-border-subtle);
  padding: 20px;
  box-shadow: -2px 0 12px rgba(0, 0, 0, 0.05);
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar > * {
  flex-shrink: 0;
}

/* 完成率卡片 */
.completion-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.progress-circle {
  display: flex;
  justify-content: center;
}

.progress-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.progress-emoji {
  font-size: 32px;
  line-height: 1;
}

.progress-percentage {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
}

.progress-status {
  font-size: 12px;
  font-weight: 600;
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  width: 100%;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
}

.stat-label {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
}

.stat-value.total {
  color: var(--color-text-secondary);
}

.stat-value.success {
  color: #10b981;
}

.stat-value.warning {
  color: var(--color-warning);
}

.stat-value.pending {
  color: var(--color-danger);
}

/* 操作按钮 */
.action-icon {
  margin-right: 6px;
  font-size: 16px;
}

/* API 卡片 */
.api-endpoint,
.api-code {
  background: #1f2937;
  color: var(--color-border-subtle);
  padding: 8px 12px;
  border-radius: 6px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 11px;
  overflow-x: auto;
  margin-top: 8px;
  white-space: pre-wrap;
  word-break: break-all;
}

.api-info {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.api-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mb-4 {
  margin-bottom: 16px;
}

/* API 模态框 */
.api-modal {
  width: 600px;
  max-width: 90vw;
}

/* 工具类 */
.mr-1 {
  margin-right: 4px;
}

.ml-2 {
  margin-left: 8px;
}

/* 卡片头部带操作 */
.card-header-with-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

/* 滚动条美化 */
:deep(.n-scrollbar-content) {
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-default) transparent;
}

:deep(.n-scrollbar-content::-webkit-scrollbar) {
  width: 6px;
}

:deep(.n-scrollbar-content::-webkit-scrollbar-thumb) {
  background: var(--color-border-default);
  border-radius: 3px;
}

:deep(.n-scrollbar-content::-webkit-scrollbar-track) {
  background: transparent;
}

/* 响应式 */
@media (max-width: 1200px) {
  .content-area.with-sidebar {
    margin-right: 320px;
  }

  .sidebar {
    width: 320px;
  }
}

@media (max-width: 768px) {
  .content-area.with-sidebar {
    margin-right: 0;
  }

  .sidebar {
    position: static;
    width: 100%;
    height: auto;
    border-left: none;
    border-top: 1px solid var(--color-border-subtle);
  }

  .navbar-content {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .page-title {
    font-size: 18px;
  }

  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
