<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { NButton, NCard, NDivider, NEmpty, NInput, NModal, NSpace, NTag, NText, NTooltip, NUpload } from 'naive-ui';
import { issuePriorityOptions, issueTypeOptions } from '@/constants/issue';
import { labeledOptions } from '@/locales/display-label';
import { useLabelTable } from '@/locales/use-label-table';
import type { IssueTemplate } from '@/constants/issueTemplates';
import { fetchProjectList } from '@/service/api';
import { fetchIssueTemplates } from '@/service/api/issue-templates';
import { type CustomFieldRow, fetchCustomFields, fetchPatchIssueCustomFields } from '@/service/api/custom-fields';
import { issueApi } from '@/service/api/issue';
import { useIssueStore } from '@/store/modules/issue';
import IssueCustomFieldsEditor from '@/components/issue/IssueCustomFieldsEditor.vue';
import MarkdownEditor from '@/components/MarkdownEditor.vue';
import MarkdownRenderer from '@/components/MarkdownRenderer.vue';
import IssueTemplateSelector from '@/components/IssueTemplateSelector.vue';
import IssueTemplateForm from '@/components/IssueTemplateForm.vue';
import type { Api } from '@/typings/api';
import { $t } from '@/locales';

defineOptions({
  name: 'IssueCreate'
});

const router = useRouter();
const route = useRoute();
const issueStore = useIssueStore();
const typeLabels = useLabelTable('page.issueType');
const typeOptions = computed(() => labeledOptions(issueTypeOptions.map(option => option.value), typeLabels.value));

// 页面状态
const loading = ref(false);
const hasUnsavedChanges = ref(false);
const showExitConfirm = ref(false);

// 项目数据
const projects = ref<Api.Project.Project[]>([]);
const projectsLoading = ref(false);

// 模板相关
const showTemplateSelector = ref(false);
const showTemplateForm = ref(false);
const selectedTemplate = ref<IssueTemplate | null>(null);
const customFieldDefs = ref<CustomFieldRow[]>([]);
const customFieldDraft = ref<Array<{ key: string; value: unknown }>>([]);
const appliedTemplateId = ref<string | null>(null);

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

// 表单引用
const titleInputRef = ref();

// UI 状态
const showPreview = ref(false);
const advancedExpanded = ref(false);

// 附件相关
const pendingFiles = ref<File[]>([]);
const uploadListRef = ref();
const isUploadingAttachments = ref(false);

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / k ** i).toFixed(1)} ${sizes[i]}`;
};

// 判断是否为图片
const isImageFile = (file: File) => {
  return file.type.startsWith('image/');
};

// 处理文件选择
const handleFileSelect = (data: { file: { file?: File; name?: string; size?: number } }) => {
  const file = data.file.file;
  if (!file) return;

  const maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    window.$message?.error('文件大小不能超过 10MB');
    return;
  }

  pendingFiles.value.push(file);
  hasUnsavedChanges.value = true;
};

// 移除待上传文件
const removePendingFile = (index: number) => {
  pendingFiles.value.splice(index, 1);
};

// 上传附件到已创建的 Issue
async function uploadPendingAttachments(issueId: string) {
  if (pendingFiles.value.length === 0) return;

  isUploadingAttachments.value = true;
  let successCount = 0;
  for (const file of pendingFiles.value) {
    try {
      // eslint-disable-next-line no-await-in-loop
      await issueApi.uploadAttachment(issueId, { file });
      successCount += 1;
    } catch (error) {
      console.error('上传附件失败:', file.name, error);
    }
  }
  isUploadingAttachments.value = false;

  if (successCount > 0 && successCount < pendingFiles.value.length) {
    window.$message?.warning(`${successCount}/${pendingFiles.value.length} 个附件上传成功`);
  }
}

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

// 打开模板选择器
function openTemplateSelector() {
  showTemplateSelector.value = true;
}

// 选择模板
function handleSelectTemplate(template: IssueTemplate) {
  selectedTemplate.value = template;
  showTemplateForm.value = true;
}

// 从模板创建 Issue
function handleCreateFromTemplate(title: string, content: string) {
  formData.value.title = title;
  formData.value.description = content;
  const tpl = selectedTemplate.value;
  if (tpl?.defaultType) {
    formData.value.type = tpl.defaultType as Api.Issue.IssueType;
  }
  if (tpl?.defaultPriority) {
    formData.value.priority = tpl.defaultPriority as Api.Issue.IssuePriority;
  }
  appliedTemplateId.value = tpl?.apiId || (tpl?.id?.includes('-') ? tpl.id : null);
  showTemplateForm.value = false;
  selectedTemplate.value = null;
  hasUnsavedChanges.value = true;
}

// 创建 Issue
function onCustomFieldDraft(rows: Array<{ key: string; value: unknown }>) {
  customFieldDraft.value = rows;
}

async function handleCreate() {
  if (!formData.value.title.trim()) {
    window.$message?.error('请输入问题标题');
    titleInputRef.value?.focus();
    return;
  }

  loading.value = true;
  try {
    const issue = await issueStore.createIssue({
      title: formData.value.title,
      description: formData.value.description,
      type: formData.value.type,
      priority: formData.value.priority,
      project_id: formData.value.project_id,
      task_id: formData.value.task_id,
      requirement_id: formData.value.requirement_id,
      assignee_id: formData.value.assignee_id,
      reporter_id: 'admin',
      template_id: appliedTemplateId.value || undefined
    });

    // 上传待上传的附件
    await uploadPendingAttachments(issue.id);

    const filled = customFieldDraft.value.filter(d => d.value !== null && d.value !== undefined && d.value !== '');
    if (filled.length) {
      try {
        await fetchPatchIssueCustomFields(
          issue.id,
          filled.map(d => ({ key: d.key, value: d.value }))
        );
      } catch {
        window.$message?.warning?.('问题已创建，但自定义字段保存失败');
      }
    }

    window.$message?.success('问题创建成功');
    hasUnsavedChanges.value = false;
    router.push({
      path: '/issue/detail',
      query: { id: issue.id }
    });
  } catch {
    window.$message?.error('问题创建失败');
  } finally {
    loading.value = false;
  }
}

// 取消并返回
function handleCancel() {
  if (hasUnsavedChanges.value) {
    showExitConfirm.value = true;
  } else {
    router.push('/issue/list');
  }
}

// 确认退出
function confirmExit() {
  hasUnsavedChanges.value = false;
  showExitConfirm.value = false;
  router.push('/issue/list');
}

// 切换预览
function togglePreview() {
  showPreview.value = !showPreview.value;
}

// 监听表单变化
watch(
  () => formData.value,
  () => {
    hasUnsavedChanges.value = true;
  },
  { deep: true }
);

// 页面挂载

function mapApiTemplateToIssueTemplate(row: {
  id: string;
  seedKey?: string | null;
  name: string;
  description?: string | null;
  icon?: string | null;
  payload?: {
    title?: string;
    description?: string;
    type?: string;
    priority?: string;
    fields?: IssueTemplate['fields'];
  };
}): IssueTemplate {
  const fallbackFields: IssueTemplate['fields'] = [
    {
      name: 'title',
      label: '标题',
      type: 'text',
      required: true,
      placeholder: row.payload?.title || '标题'
    },
    {
      name: 'description',
      label: '描述',
      type: 'textarea',
      required: false,
      placeholder: row.payload?.description || ''
    }
  ];
  return {
    id: row.id,
    apiId: row.id,
    seedKey: row.seedKey || undefined,
    name: row.name,
    description: row.description || '',
    icon: row.icon || 'i-carbon-document',
    fields: row.payload?.fields?.length ? row.payload.fields : fallbackFields,
    defaultType: row.payload?.type,
    defaultPriority: row.payload?.priority
  };
}

async function openTemplateFromQuery() {
  const pick = route.query.pickTemplate;
  if (pick === '1' || pick === 'true') {
    showTemplateSelector.value = true;
    return;
  }
  const templateId = typeof route.query.templateId === 'string' ? route.query.templateId : '';
  if (!templateId) return;
  try {
    const { data } = await fetchIssueTemplates();
    const row = data?.rows?.find(r => r.id === templateId);
    if (!row) {
      showTemplateSelector.value = true;
      return;
    }
    selectedTemplate.value = mapApiTemplateToIssueTemplate(row);
    showTemplateForm.value = true;
  } catch {
    showTemplateSelector.value = true;
  }
}

onMounted(async () => {
  fetchCustomFields().then(({ data }) => {
    customFieldDefs.value = data?.rows || [];
  });
  loadProjects();
  await openTemplateFromQuery();
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
  <div class="issue-create-page">
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
          返回列表 (Esc)
        </NTooltip>

        <NText strong style="font-size: 16px; margin-left: 12px">创建问题</NText>

        <NTag v-if="hasUnsavedChanges" type="warning" size="small" style="margin-left: 12px">未保存</NTag>
      </div>

      <div class="header-right">
        <NSpace :size="8">
          <!-- 模板按钮 -->
          <NTooltip>
            <template #trigger>
              <NButton secondary size="small" @click="openTemplateSelector">
                <template #icon>
                  <icon-mdi-file-document-outline />
                </template>
                使用模板
              </NButton>
            </template>
            从模板创建问题
          </NTooltip>

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
          <!-- 创建按钮 -->
          <NButton type="primary" :loading="loading" @click="handleCreate">
            <template #icon>
              <icon-mdi-check />
            </template>
            创建问题
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
            @submit="handleCreate"
          />
        </div>

        <NCard
          v-if="customFieldDefs.length"
          id="create-custom-fields"
          title="自定义字段（可选）"
          size="small"
          :bordered="false"
          style="margin-bottom: 12px"
        >
          <IssueCustomFieldsEditor local-only :definitions="customFieldDefs" @draft-change="onCustomFieldDraft" />
        </NCard>

        <!-- 附件上传区域 -->
        <div class="attachment-section">
          <div class="section-header">
            <NText strong>附件</NText>
            <NText depth="3" style="font-size: 12px">{{ $t('page.shell.issueUploadHint') }}</NText>
          </div>

          <!-- 已选择的文件列表 -->
          <div v-if="pendingFiles.length > 0" class="pending-files">
            <div v-for="(file, index) in pendingFiles" :key="index" class="pending-file-item">
              <div class="file-icon">
                <div
                  class="text-24px"
                  :class="
                    isImageFile(file) ? 'i-material-symbols-image-outline' : 'i-material-symbols-description-outline'
                  "
                />
              </div>
              <div class="file-info">
                <NText class="file-name" :title="file.name">{{ file.name }}</NText>
                <NText depth="3" style="font-size: 12px">{{ formatFileSize(file.size) }}</NText>
              </div>
              <NButton size="small" quaternary type="error" @click="removePendingFile(index)">
                <template #icon>
                  <icon-mdi-close />
                </template>
              </NButton>
            </div>
          </div>

          <NUpload
            ref="uploadListRef"
            :custom-request="handleFileSelect"
            :show-file-list="false"
            accept="*/*"
            :disabled="loading"
          >
            <NButton secondary size="small">
              <template #icon>
                <icon-mdi-paperclip />
              </template>
              添加附件
            </NButton>
          </NUpload>
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

    <!-- 模板选择器 -->
    <IssueTemplateSelector
      :visible="showTemplateSelector"
      @select="handleSelectTemplate"
      @close="showTemplateSelector = false"
    />

    <!-- 模板表单 -->
    <IssueTemplateForm
      :visible="showTemplateForm"
      :template="selectedTemplate"
      @submit="handleCreateFromTemplate"
      @close="showTemplateForm = false"
    />

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
.issue-create-page {
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

/* 附件区域 */
.attachment-section {
  margin-bottom: 24px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid var(--color-border-subtle);
}

.pending-files {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.pending-file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #fff;
  border: 1px solid #e8eaed;
}

.pending-file-item .file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background-color: var(--n-color-modal);
  color: var(--n-text-color);
  flex-shrink: 0;
}

.pending-file-item .file-info {
  flex: 1;
  min-width: 0;
}

.pending-file-item .file-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.property-card,
.shortcut-card {
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

/* 快捷键列表 */
.shortcut-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.shortcut-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
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
