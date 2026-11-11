<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NDivider,
  NEmpty,
  NInput,
  NModal,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  NText,
  NTooltip
} from 'naive-ui';
import { issuePriorityOptions, issueTypeOptions } from '@/constants/issue';
import { labeledOptions } from '@/locales/display-label';
import { useLabelTable } from '@/locales/use-label-table';
import { fetchProjectList } from '@/service/api';
import { useIssueStore } from '@/store/modules/issue';
import MarkdownEditor from '@/components/MarkdownEditor.vue';
import MarkdownRenderer from '@/components/MarkdownRenderer.vue';
import type { Api } from '@/typings/api';

defineOptions({
  name: 'IssueEdit'
});

const route = useRoute();
const router = useRouter();
const issueStore = useIssueStore();
const typeLabels = useLabelTable('page.issueType');
const typeOptions = computed(() => labeledOptions(issueTypeOptions.map(option => option.value), typeLabels.value));

const issueId = computed(() => (route.query.id as string) || '');

// 页面状态
const saving = ref(false);
const hasUnsavedChanges = ref(false);
const showExitConfirm = ref(false);
const pageLoading = ref(true);

// 项目数据
const projects = ref<Api.Project.Project[]>([]);
const projectsLoading = ref(false);

// 表单数据
const formData = ref<{
  title: string;
  description: string;
  type: Api.Issue.IssueType;
  priority: Api.Issue.IssuePriority;
  project_id?: string;
  task_id?: string;
  requirement_id?: string;
  assignee_id?: string;
}>({
  title: '',
  description: '',
  type: 'bug' as Api.Issue.IssueType,
  priority: 'medium' as Api.Issue.IssuePriority,
  project_id: undefined,
  task_id: undefined,
  requirement_id: undefined,
  assignee_id: undefined
});

// 原始数据用于比较是否有变更
const originalData = ref<{
  title: string;
  description: string;
  type: Api.Issue.IssueType;
  priority: Api.Issue.IssuePriority;
  project_id?: string;
  task_id?: string;
  requirement_id?: string;
  assignee_id?: string;
}>({
  title: '',
  description: '',
  type: 'bug' as Api.Issue.IssueType,
  priority: 'medium' as Api.Issue.IssuePriority,
  project_id: undefined,
  task_id: undefined,
  requirement_id: undefined,
  assignee_id: undefined
});

// 表单引用
const titleInputRef = ref();

// UI 状态
const showPreview = ref(false);
const advancedExpanded = ref(false);

// 项目选项
const projectOptions = computed(() => {
  return projects.value.map(p => ({
    label: p.name,
    value: p.id
  }));
});

// 类型图标映射
const typeIconMap: Record<Api.Issue.IssueType, string> = {
  bug: 'mdi:bug',
  feature: 'mdi:auto-fix',
  improvement: 'mdi:trending-up',
  task: 'mdi:checkbox-marked-circle-outline',
  documentation: 'mdi:book-open-outline'
};

// 优先级颜色映射
const priorityColorMap: Record<Api.Issue.IssuePriority, string> = {
  critical: '#d03050',
  high: '#f0a020',
  medium: '#18a058',
  low: '#72a0c0'
};

// 加载项目列表
async function loadProjects() {
  projectsLoading.value = true;
  try {
    const response = await fetchProjectList();
    projects.value = response.data || [];
  } catch {
    projects.value = [];
  } finally {
    projectsLoading.value = false;
  }
}

// 加载 Issue 数据
async function loadIssueForEdit() {
  if (!issueId.value) {
    window.$message?.error('缺少问题 ID');
    router.push('/issue/list');
    return;
  }

  pageLoading.value = true;
  try {
    const data = await issueStore.getIssue(issueId.value);

    // 填充表单
    formData.value = {
      title: data.title,
      description: data.description || '',
      type: data.type,
      priority: data.priority,
      project_id: data.project_id || undefined,
      task_id: data.task_id || undefined,
      requirement_id: data.requirement_id || undefined,
      assignee_id: data.assignee_id || undefined
    };

    // 保存原始数据
    originalData.value = { ...formData.value };
    hasUnsavedChanges.value = false;
  } catch {
    window.$message?.error('加载问题数据失败');
    router.push('/issue/list');
  } finally {
    pageLoading.value = false;
  }
}

// 保存 Issue
async function handleSave() {
  if (!formData.value.title.trim()) {
    window.$message?.error('请输入问题标题');
    titleInputRef.value?.focus();
    return;
  }

  saving.value = true;
  try {
    await issueStore.updateIssue(issueId.value, {
      title: formData.value.title,
      description: formData.value.description,
      type: formData.value.type,
      priority: formData.value.priority,
      project_id: formData.value.project_id,
      task_id: formData.value.task_id,
      requirement_id: formData.value.requirement_id,
      assignee_id: formData.value.assignee_id
    });

    window.$message?.success('问题更新成功');
    hasUnsavedChanges.value = false;
    router.push({
      path: '/issue/detail',
      query: { id: issueId.value }
    });
  } catch {
    window.$message?.error('问题更新失败');
  } finally {
    saving.value = false;
  }
}

// 取消并返回
function handleCancel() {
  if (hasUnsavedChanges.value) {
    showExitConfirm.value = true;
  } else {
    router.push({
      path: '/issue/detail',
      query: { id: issueId.value }
    });
  }
}

// 确认退出
function confirmExit() {
  hasUnsavedChanges.value = false;
  showExitConfirm.value = false;
  router.push({
    path: '/issue/detail',
    query: { id: issueId.value }
  });
}

// 切换预览
function togglePreview() {
  showPreview.value = !showPreview.value;
}

// 监听表单变化
watch(
  () => formData.value,
  () => {
    // 比较当前数据和原始数据
    hasUnsavedChanges.value = JSON.stringify(formData.value) !== JSON.stringify(originalData.value);
  },
  { deep: true }
);

// 页面挂载
onMounted(() => {
  loadProjects();
  loadIssueForEdit();
  // 自动聚焦标题输入框
  nextTick(() => {
    titleInputRef.value?.focus();
  });
});

// 页面卸载前确认
onBeforeRouteLeave((_to, _from, next) => {
  if (hasUnsavedChanges.value && !showExitConfirm.value) {
    showExitConfirm.value = true;
    next(false);
  } else {
    next();
  }
});
</script>

<template>
  <div class="issue-edit-page">
    <!-- 页面加载状态 -->
    <NSpin :show="pageLoading" description="加载中...">
      <!-- 顶部工具栏 -->
      <div class="page-header">
        <div class="header-left">
          <NTooltip>
            <template #trigger>
              <NButton quaternary circle size="small" @click="handleCancel">
                <template #icon>
                  <icon-mdi-arrow-left />
                </template>
              </NButton>
            </template>
            返回详情 (Esc)
          </NTooltip>

          <NText strong style="font-size: 16px; margin-left: 12px">编辑问题</NText>

          <NTag v-if="hasUnsavedChanges" type="warning" size="small" style="margin-left: 12px">未保存</NTag>
        </div>

        <div class="header-right">
          <NSpace :size="8">
            <!-- 预览切换 -->
            <NTooltip>
              <template #trigger>
                <NButton secondary size="small" @click="togglePreview">
                  <template #icon>
                    <icon-mdi-eye-outline v-if="!showPreview" />
                    <icon-mdi-pencil-outline v-else />
                  </template>
                </NButton>
              </template>
              {{ showPreview ? '编辑模式' : '预览模式' }}
            </NTooltip>

            <!-- 保存按钮 -->
            <NButton type="primary" :loading="saving" @click="handleSave">
              <template #icon>
                <icon-mdi-check />
              </template>
              保存更改
            </NButton>
          </NSpace>
        </div>
      </div>

      <!-- 主内容区 -->
      <div class="page-content">
        <!-- 左侧主内容 -->
        <div class="main-content">
          <!-- 标题输入 -->
          <div class="title-section">
            <input
              ref="titleInputRef"
              v-model="formData.title"
              class="title-input"
              placeholder="输入问题标题..."
              maxlength="200"
            />
            <div class="title-hint">
              <NText depth="3">{{ formData.title.length }} / 200</NText>
            </div>
          </div>

          <!-- 描述编辑器 -->
          <div v-show="!showPreview" class="description-section">
            <div class="section-header">
              <NText strong>描述</NText>
              <NText depth="3" style="font-size: 12px">支持 Markdown 语法，+ 引用其他资源</NText>
            </div>
            <MarkdownEditor
              v-model="formData.description"
              placeholder="详细描述这个问题..."
              :max-height="400"
              @submit="handleSave"
            />
          </div>

          <!-- 预览模式 -->
          <div v-show="showPreview" class="preview-section">
            <div class="section-header">
              <NText strong>预览</NText>
            </div>
            <div class="preview-content">
              <MarkdownRenderer v-if="formData.description" :content="formData.description" />
              <NEmpty v-else description="暂无描述内容" />
            </div>
          </div>
        </div>

        <!-- 右侧属性面板 -->
        <div class="sidebar">
          <NCard :bordered="false" class="property-card">
            <template #header>
              <NSpace align="center">
                <icon-mdi-cog />
                <NText strong>属性设置</NText>
              </NSpace>
            </template>

            <!-- 类型选择 -->
            <div class="property-item">
              <div class="property-label">
                <NText depth="3" style="font-size: 12px">类型</NText>
              </div>
              <NSelect v-model:value="formData.type" :options="typeOptions" size="small" placeholder="选择类型">
                <template #label="{ option }">
                  <NSpace :size="8" align="center">
                    <icon-mdi v-if="option?.value" :name="typeIconMap[option.value as Api.Issue.IssueType]" />
                    <span>{{ option?.label }}</span>
                  </NSpace>
                </template>
              </NSelect>
            </div>

            <!-- 优先级选择 -->
            <div class="property-item">
              <div class="property-label">
                <NText depth="3" style="font-size: 12px">优先级</NText>
              </div>
              <NSelect
                v-model:value="formData.priority"
                :options="issuePriorityOptions"
                size="small"
                placeholder="选择优先级"
              >
                <template #label="{ option }">
                  <NSpace :size="8" align="center">
                    <div
                      v-if="option?.value"
                      class="priority-dot"
                      :style="{ backgroundColor: priorityColorMap[option.value as Api.Issue.IssuePriority] }"
                    />
                    <span>{{ option?.label }}</span>
                  </NSpace>
                </template>
              </NSelect>
            </div>

            <NDivider style="margin: 16px 0" />

            <!-- 关联项目 -->
            <div class="property-item">
              <div class="property-label">
                <NText depth="3" style="font-size: 12px">关联项目</NText>
              </div>
              <NSelect
                v-model:value="formData.project_id"
                :options="projectOptions"
                size="small"
                placeholder="选择项目（可选）"
                :loading="projectsLoading"
                clearable
                filterable
              />
            </div>

            <!-- 高级选项 -->
            <div class="property-item">
              <NButton
                text
                size="small"
                style="width: 100%; justify-content: space-between; padding: 8px 0"
                @click="advancedExpanded = !advancedExpanded"
              >
                <NText depth="3" style="font-size: 12px">高级选项</NText>
                <icon-mdi-chevron-down :class="{ expanded: advancedExpanded }" />
              </NButton>
            </div>

            <template v-if="advancedExpanded">
              <!-- 关联任务 -->
              <div class="property-item">
                <div class="property-label">
                  <NText depth="3" style="font-size: 12px">关联任务 ID</NText>
                </div>
                <NInput v-model:value="formData.task_id" size="small" placeholder="输入任务 ID" clearable />
              </div>

              <!-- 关联需求 -->
              <div class="property-item">
                <div class="property-label">
                  <NText depth="3" style="font-size: 12px">关联需求 ID</NText>
                </div>
                <NInput v-model:value="formData.requirement_id" size="small" placeholder="输入需求 ID" clearable />
              </div>

              <!-- 负责人 -->
              <div class="property-item">
                <div class="property-label">
                  <NText depth="3" style="font-size: 12px">负责人 ID</NText>
                </div>
                <NInput v-model:value="formData.assignee_id" size="small" placeholder="输入负责人 ID" clearable />
              </div>
            </template>
          </NCard>
        </div>
      </div>
    </NSpin>

    <!-- 退出确认对话框 -->
    <NModal
      v-model:show="showExitConfirm"
      preset="dialog"
      title="确认退出"
      content="你有未保存的更改，确定要退出吗？"
      positive-text="放弃更改"
      negative-text="继续编辑"
      @positive-click="confirmExit"
    />
  </div>
</template>

<style scoped>
.issue-edit-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f7fa;
}

/* 顶部工具栏 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #e8eaed;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

/* 主内容区 */
.page-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 左侧主内容 */
.main-content {
  flex: 1;
  padding: 32px 48px;
  overflow-y: auto;
  background: #fff;
}

/* 标题区域 */
.title-section {
  margin-bottom: 32px;
}

.title-input {
  width: 100%;
  font-size: 32px;
  font-weight: 600;
  line-height: 1.3;
  color: #1a1a1a;
  border: none;
  outline: none;
  background: transparent;
  font-family:
    -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans',
    'Helvetica Neue', sans-serif;
}

.title-input::placeholder {
  color: #aaa;
}

.title-input:focus {
  outline: none;
}

.title-hint {
  margin-top: 8px;
  text-align: right;
}

/* 描述区域 */
.description-section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

/* 预览区域 */
.preview-section {
  margin-bottom: 24px;
}

.preview-content {
  padding: 20px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid var(--color-border-subtle);
  min-height: 200px;
}

/* 右侧边栏 */
.sidebar {
  width: 320px;
  padding: 24px;
  background: #f5f7fa;
  border-left: 1px solid #e8eaed;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.property-card {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.property-item {
  margin-bottom: 16px;
}

.property-item:last-child {
  margin-bottom: 0;
}

.property-label {
  margin-bottom: 6px;
}

/* 优先级圆点 */
.priority-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

/* 展开/收起动画 */
.icon-mdi-chevron-down {
  transition: transform 0.3s ease;
}

.icon-mdi-chevron-down.expanded {
  transform: rotate(180deg);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .main-content {
    padding: 24px;
  }

  .sidebar {
    width: 280px;
    padding: 16px;
  }

  .title-input {
    font-size: 28px;
  }
}

@media (max-width: 768px) {
  .page-content {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    border-left: none;
    border-top: 1px solid #e8eaed;
  }

  .main-content {
    padding: 20px;
  }

  .title-input {
    font-size: 24px;
  }
}

/* 滚动条样式 */
.main-content::-webkit-scrollbar,
.sidebar::-webkit-scrollbar {
  width: 6px;
}

.main-content::-webkit-scrollbar-track,
.sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.main-content::-webkit-scrollbar-thumb,
.sidebar::-webkit-scrollbar-thumb {
  background: var(--color-border-default);
  border-radius: 3px;
}

.main-content::-webkit-scrollbar-thumb:hover,
.sidebar::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-tertiary);
}
</style>
