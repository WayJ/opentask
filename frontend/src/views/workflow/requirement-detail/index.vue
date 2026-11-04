<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { NAlert, NButton, NCard, NEmpty, NSpace, NSpin, NTag, NTooltip } from 'naive-ui';
import { getRequirementPriorityText, requirementStatusTextMap } from '@/constants/requirement';
import type { Task as _Task } from '@/service/api/requirement';
import { useRequirementStore } from '@/store/modules/requirement';
import type { Document } from '@/typings/api/document';
import MarkdownRenderer from '@/components/MarkdownRenderer.vue';
import DocDrawer from '@/components/DocDrawer.vue';
import TaskCard from './components/TaskCard.vue';
import DocumentEditModal from './components/DocumentEditModal.vue';
import ImportResultModal from './components/ImportResultModal.vue';
import TaskFormModal from './components/TaskFormModal.vue';
import RequirementQuickEdit from './components/RequirementQuickEdit.vue';
import CommentsCard from './components/CommentsCard.vue';
import CreatePGETaskModal from './components/CreatePGETaskModal.vue';
import DescriptionEditModal from './components/DescriptionEditModal.vue';
import { useDocumentManagement } from './composables/useDocumentManagement';
import { useRequirementDetail } from './composables/useRequirementDetail';
import { useTaskManagement } from './composables/useTaskManagement';
import { useComments } from './composables/useComments';

// 使用公共常量
const requirementStatusMap = requirementStatusTextMap;

const route = useRoute();
const requirementId = computed(() => (route.query.id as string) || '');
const requirementCode = computed(() => (route.query.code as string) || '');

// 文档编辑弹窗 ref（用于重置上传状态）- 必须在 composable 之前定义
const documentEditModalRef = ref<{ resetUploadingState: () => void } | null>(null);

// 使用需求详情 composable - 支持 id 或 code 参数
const { requirement, loading, error, loadRequirement } = useRequirementDetail(requirementId, requirementCode);

// 使用文档管理 composable
const {
  documents,
  showDocumentModal,
  selectedDocument,
  editDocumentForm,
  showDocumentEdit,
  documentLoading,
  viewDocument,
  openDocumentEdit,
  closeDocumentEdit: _closeDocumentEdit,
  closeDocumentModal: _closeDocumentModal,
  saveDocument,
  batchSaveDocuments,
  deleteDocument: _deleteDocument,
  getDocumentDownloadUrl
} = useDocumentManagement(requirement, {
  entityType: 'requirement',
  onSave: async () => {
    await loadRequirement();
  },
  onUploadComplete: () => {
    // 上传完成后重置 DocumentEditModal 的上传状态
    documentEditModalRef.value?.resetUploadingState();
  }
});

// 使用任务管理 composable
const {
  tasks,
  tasksLoading,
  showCreateModal,
  showCreateSubTaskModal,
  parentTaskForSub,
  createForm,
  showEditModal,
  editTask: _editTask,
  editForm,
  importUploading: _importUploading,
  importResult: _importResult,
  showImportResult: _showImportResult,
  taskTypeOptions,
  taskStatusOptions,
  taskTree,
  taskProgress,
  loadTasks,
  openCreateSubTaskModal,
  handleCreateTask,
  handleCreateSubTask,
  openEditModal,
  handleUpdateTask,
  handleDeleteTask,
  handleStartTask,
  handleCompleteTask,
  handleImportTasks: _handleImportTasks
} = useTaskManagement(requirementId);

// 使用评论管理 composable
const { comments, commentsLoading, loadComments, handleAddComment } = useComments(requirementId);

// 使用需求 store
const requirementStore = useRequirementStore();

// PGE 任务创建弹窗状态
const showCreatePGETaskModal = ref(false);

// 描述编辑模态框状态
const showDescriptionEdit = ref(false);
const descriptionEditing = ref(false);
const tempDescription = ref('');

onMounted(async () => {
  await loadRequirement();
  loadTasks();
  loadComments();
});

// 处理文档保存（包含附件）
async function handleSaveDocument(file?: File) {
  // 编辑现有文档：单文件上传
  if (editDocumentForm.id) {
    await saveDocument(file);
  }
}

// 处理批量文档保存（新建文档时多文件上传）
async function handleBatchSaveDocuments(files: File[]) {
  // 新建文档：多文件上传
  if (!editDocumentForm.id) {
    const result = await batchSaveDocuments(files);
    // 显示上传结果
    if (result.success > 0) {
      window.$message?.success(
        `成功上传 ${result.success} 个文件${result.failed > 0 ? `，${result.failed} 个文件失败` : ''}`
      );
      // 上传成功后关闭对话框
      showDocumentEdit.value = false;
    }
    if (result.failed > 0 && result.errors.length > 0) {
      // 显示错误信息
      console.error('部分文件上传失败:', result.errors);
    }
  }
}

// 处理删除文档
function handleDeleteDocument(doc: any) {
  window.$dialog?.warning({
    title: '确认删除',
    content: `确定要删除文档 "${doc.file_name || '未命名文档'}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await _deleteDocument(doc.id);
        window.$message?.success('文档删除成功');
      } catch {
        window.$message?.error('文档删除失败');
      }
    }
  });
}

// 处理文档切换 - 直接使用列表中的数据，避免不必要的 API 调用
async function handleDocumentChange(doc: Document.Response | null) {
  if (!doc) {
    selectedDocument.value = null;
    showDocumentModal.value = false;
    return;
  }
  // 直接使用传入的文档对象，不需要再次调用 API
  selectedDocument.value = doc;
  showDocumentModal.value = true;
}

// 打开描述编辑
function openDescriptionEdit() {
  if (requirement.value) {
    tempDescription.value = requirement.value.description || '';
    showDescriptionEdit.value = true;
  }
}

// 保存描述
async function handleSaveDescription(newDescription: string) {
  if (!requirement.value) return;

  descriptionEditing.value = true;

  try {
    await requirementStore.editRequirement(requirement.value.id, {
      description: newDescription
    });
    await loadRequirement();
    window.$message?.success('描述更新成功');
    showDescriptionEdit.value = false;
  } catch (err) {
    console.error('保存描述失败:', err);
    window.$message?.error('保存描述失败');
  } finally {
    descriptionEditing.value = false;
  }
}

// 检查是否已存在PGE任务（需求2026-122）
const hasPGETask = computed(() => {
  if (!tasks.value || tasks.value.length === 0) return false;
  return tasks.value.some((task: any) => task.framework === 'PGE' && !task.parent_id);
});
</script>

<template>
  <div class="requirement-detail-container">
    <div class="requirement-detail-main">
      <NSpin :show="loading">
        <NCard v-if="requirement" title="需求详情" class="mb-3">
          <!-- 紧凑表格：基本信息 -->
          <div class="info-table">
            <div class="info-row">
              <div class="info-cell label">需求编号</div>
              <div class="info-cell value">{{ requirement.code }}</div>
              <div class="info-cell label">标题</div>
              <div class="info-cell value">{{ requirement.title }}</div>
            </div>
            <div class="info-row">
              <div class="info-cell label">状态</div>
              <div class="info-cell value">
                <NTag :type="requirement.status === 'draft' ? 'default' : 'success'" size="small">
                  {{ requirementStatusMap[requirement.status] || requirement.status }}
                </NTag>
              </div>
              <div class="info-cell label">优先级</div>
              <div class="info-cell value">
                {{ requirement.priority ? getRequirementPriorityText(requirement.priority) : '-' }}
              </div>
            </div>
            <!--
 <div class="info-row">
              <div class="info-cell label">创建时间</div>
              <div class="info-cell value">{{ new Date(requirement.created_at).toLocaleString() }}</div>
              <div class="info-cell label">归属项目</div>
              <div class="info-cell value">
                <NSpace v-if="requirement.project_ids && requirement.project_ids.length > 0" :size="4">
                  <NTag v-for="projectId in requirement.project_ids" :key="projectId" size="small" type="info">
                    项目 ID: {{ projectId.slice(0, 8) }}...
                  </NTag>
                </NSpace>
                <span v-else class="text-placeholder">未归属项目</span>
              </div>
            </div> 
-->
          </div>

          <!-- 描述 -->
          <div class="description-section mt-3">
            <div class="section-header-with-action">
              <span class="section-label">描述</span>
              <NButton size="tiny" quaternary type="primary" @click="openDescriptionEdit">
                <template #icon>
                  <icon-mdi-pencil />
                </template>
                编辑
              </NButton>
            </div>
            <div v-if="requirement.description" class="description-content">
              <MarkdownRenderer :content="requirement.description" />
            </div>
            <div v-else class="description-empty">
              <NText depth="3">暂无描述</NText>
            </div>
          </div>

          <!-- 相关文档 -->
          <div class="documents-section mt-3">
            <div class="section-header-with-action">
              <span class="section-label">相关文档 ({{ documents.length }})</span>
              <NButton size="tiny" quaternary @click="openDocumentEdit()">
                <template #icon>
                  <span class="text-xs">+</span>
                </template>
                添加文档
              </NButton>
            </div>
            <div v-if="documents.length > 0" class="document-list-compact">
              <div v-for="doc in documents" :key="doc.id" class="document-item-compact">
                <a href="#" class="document-link-compact" @click.prevent="viewDocument(doc)">
                  📄 {{ doc.file_name || '未命名文档' }}
                </a>
                <NButton
                  size="tiny"
                  quaternary
                  type="error"
                  class="document-delete-btn"
                  @click="handleDeleteDocument(doc)"
                >
                  <template #icon>
                    <icon-mdi-delete />
                  </template>
                </NButton>
              </div>
            </div>
            <NEmpty v-else description="暂无文档" size="small" />
          </div>
        </NCard>
        <!-- 错误状态：需求不存在 -->
        <NAlert v-else-if="error" type="error" class="mt-3">
          <template #header>未找到需求</template>
          请检查链接是否正确，或联系管理员确认需求是否存在。
        </NAlert>
      </NSpin>

      <!-- 任务管理 - 卡片样式 -->
      <NCard>
        <template #header>
          <div class="card-header">
            <div class="task-header-title">
              <span>任务管理</span>
              <NSpin :show="tasksLoading" size="small">
                <span class="task-progress-inline">
                  · {{ taskProgress.completed }}/{{ taskProgress.total }} 已完成
                  <span v-if="taskProgress.inProgress > 0" class="text-neutral-500">
                    · {{ taskProgress.inProgress }} 进行中
                  </span>
                </span>
              </NSpin>
            </div>
            <NSpace>
              <!-- 批量导入功能已隐藏，改用 PGE 任务创建 -->
              <!--
 <NUpload
                :custom-request="handleImportTasks"
                :show-file-list="false"
                accept=".json"
                :disabled="importUploading"
              >
                <NButton :loading="importUploading" size="small">
                  {{ importUploading ? '导入中...' : '批量导入' }}
                </NButton>
              </NUpload> 
-->
              <NButton tertiary size="small" :disabled="hasPGETask" @click="showCreatePGETaskModal = true">
                创建任务（遗留·已弃用）
              </NButton>
              <NTooltip v-if="hasPGETask" trigger="hover">
                <template #trigger>
                  <span class="text-xs text-neutral-500">每个需求最多只能创建一个PGE任务</span>
                </template>
                已存在PGE任务，无法创建更多
              </NTooltip>
            </NSpace>
          </div>
        </template>

        <NSpin :show="tasksLoading">
          <div v-if="tasks.length > 0" class="task-cards">
            <TaskCard
              v-for="task in taskTree"
              :key="task.id"
              :task="task"
              @start="handleStartTask"
              @complete="handleCompleteTask"
              @edit="openEditModal"
              @add-subtask="openCreateSubTaskModal"
              @delete="handleDeleteTask"
              @view-document="viewDocument"
            />
          </div>
          <NAlert v-else-if="!tasksLoading" type="info" class="mt-4">暂无任务，点击"创建任务"开始创建</NAlert>
        </NSpin>
      </NCard>

      <!-- 评论卡片 -->
      <CommentsCard
        v-if="requirement"
        :requirement-id="requirementId"
        :comments="comments"
        :loading="commentsLoading"
        @add="handleAddComment"
      />

      <!-- 任务表单模态框 -->
      <TaskFormModal
        v-model:show="showCreateModal"
        mode="create"
        :form-data="createForm"
        :task-type-options="taskTypeOptions"
        @confirm="handleCreateTask"
      />
      <TaskFormModal
        v-model:show="showCreateSubTaskModal"
        mode="createSub"
        :parent-task="parentTaskForSub"
        :form-data="createForm"
        :task-type-options="taskTypeOptions"
        @confirm="handleCreateSubTask"
      />
      <TaskFormModal
        v-model:show="showEditModal"
        mode="edit"
        :form-data="editForm"
        :task-type-options="taskTypeOptions"
        :task-status-options="taskStatusOptions"
        @confirm="handleUpdateTask"
      />

      <!-- 导入结果模态框 -->
      <ImportResultModal v-model:show="showImportResult" :result="importResult" />

      <!-- 文档查看抽屉 -->
      <DocDrawer
        v-model:show="showDocumentModal"
        :document="selectedDocument"
        :documents="documents"
        :requirement-id="requirementId"
        :requirement-code="requirement?.code"
        :loading="documentLoading"
        :get-download-url="getDocumentDownloadUrl"
        :enable-quick-upload="true"
        :enable-delete="true"
        @update:document="handleDocumentChange"
        @document-uploaded="loadRequirement"
        @document-deleted="loadRequirement"
        @edit="openDocumentEdit"
      />

      <!-- 文档编辑模态框 -->
      <DocumentEditModal
        ref="documentEditModalRef"
        v-model:show="showDocumentEdit"
        :form="editDocumentForm"
        :multiple="!editDocumentForm.id"
        @confirm="handleSaveDocument"
        @batch-confirm="handleBatchSaveDocuments"
      />

      <!-- 创建Agent任务对话框 -->
      <CreatePGETaskModal
        v-model:show="showCreatePGETaskModal"
        :requirement-id="requirementId"
        :requirement-title="requirement?.title"
        @success="loadTasks"
      />

      <!-- 描述编辑对话框 -->
      <DescriptionEditModal
        v-model:show="showDescriptionEdit"
        :description="requirement?.description || ''"
        :loading="descriptionEditing"
        @save="handleSaveDescription"
      />
    </div>

    <!-- 右侧边栏 -->
    <div class="requirement-detail-sidebar">
      <RequirementQuickEdit v-if="requirement" :requirement="requirement" @refresh="loadRequirement" />
    </div>
  </div>
</template>

<style scoped>
.requirement-detail-container {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: var(--space-xl);
  padding: var(--space-md);
  background: var(--color-bg-secondary);
  min-height: 100vh;
  width: 100%;
}

.requirement-detail-main {
  min-width: 0;
}

.requirement-detail-sidebar {
  position: sticky;
  top: var(--space-md);
  align-self: start;
}

@media (max-width: 1200px) {
  .requirement-detail-container {
    grid-template-columns: 1fr;
  }

  .requirement-detail-sidebar {
    position: static;
  }
}
</style>

<style scoped>
/* 保留原有的局部样式 */

.mb-4 {
  margin-bottom: var(--space-md);
}

.mt-2 {
  margin-top: var(--space-sm);
}

.mt-3 {
  margin-top: var(--space-md);
}

.mt-4 {
  margin-top: var(--space-lg);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.task-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-progress-inline {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

/* 紧凑表格样式 - 紧凑风格 */
.info-table {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-bg-primary);
  box-shadow: var(--shadow-sm);
}

.info-row {
  display: grid;
  grid-template-columns: 90px 1fr 90px 1fr;
  border-bottom: 1px solid var(--color-border-subtle);
  transition: background 0.2s ease;
}

.info-row:last-child {
  border-bottom: none;
}

.info-row:hover {
  background: var(--color-bg-hover);
}

.info-cell {
  padding: var(--space-xs) var(--space-sm);
  display: flex;
  align-items: center;
  border-right: 1px solid var(--color-border-subtle);
}

.info-cell:last-child {
  border-right: none;
}

.info-cell.label {
  background-color: var(--color-bg-secondary);
  font-weight: 500;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.info-cell.value {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.info-cell[colspan='3'] {
  grid-column: span 3;
}

.text-placeholder {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

/* 描述区域 - 紧凑风格 */
.description-section {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  background: var(--color-bg-primary);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease;
}

.description-section:hover {
  box-shadow: var(--shadow-md);
}

.section-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-sm);
}

.description-content {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  line-height: 1.6;
}

/* 确保 MarkdownRenderer 内部样式不被覆盖 */
.description-content :deep(.markdown-body) {
  white-space: normal;
}

/* 文档区域 - 紧凑风格 */
.documents-section {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  background: var(--color-bg-primary);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease;
}

.documents-section:hover {
  box-shadow: var(--shadow-md);
}

.section-header {
  margin-bottom: var(--space-sm);
}

/* 带操作按钮的标题栏 - 紧凑风格 */
.section-header-with-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-sm);
  gap: var(--space-sm);
}

.section-header-with-action .section-label {
  flex: 1;
}

/* 文档列表样式 - 现代简洁风格 */
.document-list-compact {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.document-item-compact {
  display: flex;
  align-items: center;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  transition: background 0.2s ease;
}

.document-item-compact:hover {
  background: var(--color-bg-hover);
}

.document-link-compact {
  color: var(--color-success);
  text-decoration: none;
  font-size: var(--font-size-sm);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  font-weight: 500;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: inline-block;
  width: 100%;

  /* 增强视觉层次 */
  letter-spacing: 0.01em;
  position: relative;

  /* 添加背景色 */
  background-color: transparent;
  border: 1px solid transparent;
}

/* 悬停效果 */
.document-link-compact:hover {
  /* 背景色变化 */
  background-color: #e8f8f0;

  /* 文字颜色加深 */
  color: #0c7a52;

  /* 添加边框 */
  border-color: #d0f0e8;

  /* 下划线动画 */
  text-decoration: none;
}

/* 点击反馈 */
.document-link-compact:active {
  background-color: #d0f0e8;
}

/* 元数据内容 */
.meta-content {
  font-size: 13px;
  color: #666;
}

/* 文档列表样式（保留用于其他地方） */
.document-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.document-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.document-link {
  color: #18a058;
  text-decoration: none;
  transition: color 0.2s;
}

.document-link:hover {
  color: #36ad6a;
  text-decoration: underline;
}

.document-actions {
  display: flex;
  gap: 4px;
}

/* ============================================================================
   现代化任务卡片设计
   ============================================================================ */

/* 任务卡片容器 */
.task-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 现代化任务卡片主容器 */
.modern-task-card {
  position: relative;
  display: flex;
  background: #ffffff;
  border-radius: 12px;
  box-shadow:
    0 1px 3px rgba(0, 0, 0, 0.08),
    0 1px 2px rgba(0, 0, 0, 0.04);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  border: 1px solid #f0f0f0;
}

.modern-task-card:hover {
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.12),
    0 4px 8px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
  border-color: #e0e0e0;
}

/* 状态指示条 */
.task-status-indicator {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, var(--status-color) 0%, var(--status-color-light, var(--status-color)) 100%);
}

.task-status-indicator.status-pending {
  --status-color: #94a3b8;
  --status-color-light: #cbd5e1;
}

.task-status-indicator.status-assigned {
  --status-color: var(--color-primary);
  --status-color-light: #93c5fd;
}

.task-status-indicator.status-running {
  --status-color: var(--color-warning);
  --status-color-light: #fbbf24;
}

.task-status-indicator.status-completed {
  --status-color: #10b981;
  --status-color-light: #6ee7b7;
}

.task-status-indicator.status-failed {
  --status-color: var(--color-danger);
  --status-color-light: #f87171;
}

.task-status-indicator.status-blocked {
  --status-color: var(--color-info);
  --status-color-light: #c4b5fd;
}

.task-status-indicator.status-cancelled {
  --status-color: var(--color-text-secondary);
  --status-color-light: var(--color-text-tertiary);
}

/* 卡片主内容区域 */
.task-card-main {
  flex: 1;
  padding: 16px 16px 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 顶部行：状态和类型 */
.task-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.task-left-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 任务编号 */
.task-code {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
  letter-spacing: 0.5px;
}

/* 状态徽章 */
.task-status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.2s ease;
}

.task-status-badge.status-pending {
  background: #f1f5f9;
  color: #64748b;
}

.task-status-badge.status-assigned {
  background: #dbeafe;
  color: var(--color-primary-active);
}

.task-status-badge.status-running {
  background: #fef3c7;
  color: #d97706;
}

.task-status-badge.status-completed {
  background: #d1fae5;
  color: #059669;
}

.task-status-badge.status-failed {
  background: #fee2e2;
  color: #dc2626;
}

.task-status-badge.status-blocked {
  background: #ede9fe;
  color: #7c3aed;
}

.task-status-badge.status-cancelled {
  background: #f3f4f6;
  color: #4b5563;
}

/* 类型徽章 */
.task-type-badge {
  padding: 4px 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #ffffff;
  font-size: 11px;
  font-weight: 600;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
}

/* 任务标题 */
.task-title-heading {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
  letter-spacing: -0.01em;
}

/* 任务描述 */
.task-description {
  color: #64748b;
  line-height: 1.6;
  font-size: 14px;
}

.task-description :deep(p:last-child) {
  margin-bottom: 0;
}

/* 文档区域 */
.task-documents-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.task-documents-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.document-icon,
.subtasks-icon {
  font-size: 16px;
  color: #64748b;
  vertical-align: middle;
}

.task-documents-count {
  background: #e2e8f0;
  color: #475569;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.task-document-links {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-document-link {
  color: #0891b2;
  text-decoration: none;
  font-size: 13px;
  padding: 6px 10px;
  border-radius: 6px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  font-weight: 500;
  border: 1px solid transparent;
  position: relative;
}

.task-document-link::before {
  content: '📄';
  margin-right: 6px;
  font-size: 12px;
}

.task-document-link:hover {
  background: #ecfeff;
  color: #0e7490;
  border-color: #cbd5e1;
  transform: translateX(4px);
  box-shadow: 0 2px 4px rgba(8, 145, 178, 0.1);
}

/* 子任务区域 */
.subtasks-section {
  margin-top: 4px;
  padding: 12px;
  background: #fefce8;
  border-radius: 8px;
  border: 1px solid #fef08a;
}

.subtasks-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #854d0e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.subtasks-collapse :deep(.n-collapse-item) {
  background: transparent;
  border: none;
}

.subtasks-collapse :deep(.n-collapse-item__header) {
  padding: 0;
  font-size: 13px;
  font-weight: 500;
  color: #713f12;
}

/* 操作栏 */
.task-actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  margin-top: 4px;
}

.task-primary-actions {
  display: flex;
  gap: 8px;
}

.task-secondary-actions {
  display: flex;
  gap: 4px;
}

/* 兼容旧样式 */
.task-card {
  transition: all 0.2s ease;
  border: 1px solid #e8e8e8;
}

.task-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border-color: #d0d0d0;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 4px;
  padding-bottom: 4px;
  border-bottom: 1px solid #f0f0f0;
}

.task-title {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 6px;
}

.task-title-text {
  font-weight: 500;
  font-size: 14px;
  color: #333;
}

.task-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: #999;
  align-items: center;
  background: #fafafa;
  padding: 2px 6px;
  border-radius: 4px;
}

.task-meta-item {
  display: inline-block;
}

.task-description {
  color: #666;
  line-height: 1.5;
  white-space: pre-wrap;
  font-size: 13px;
  margin-bottom: 6px;
  padding: 6px;
  background-color: #f9f9f9;
  border-radius: 4px;
  border-left: 3px solid #18a058;
}

.task-documents {
  padding: 6px 8px;
  background-color: #fafafa;
  border-radius: 4px;
  border: 1px solid #f0f0f0;
  margin-bottom: 6px;
}

.task-documents-title {
  font-size: 11px;
  font-weight: 500;
  color: #999;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.task-document-links {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.task-document-link {
  /* 基础样式 */
  color: #18a058;
  text-decoration: none;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  gap: 6px;

  /* 字体加粗 */
  font-weight: 500;

  /* 边框 */
  border: 1px solid transparent;

  /* 位置相对，用于下划线动画 */
  position: relative;
}

/* 悬停效果 */
.task-document-link:hover {
  /* 背景色 */
  background-color: rgba(24, 160, 88, 0.08);

  /* 文字颜色加深 */
  color: #0c7a52;

  /* 添加边框 */
  border-color: rgba(24, 160, 88, 0.2);

  /* 轻微阴影 */
  box-shadow: 0 2px 4px rgba(24, 160, 88, 0.08);

  /* 向右移动 */
  transform: translateX(3px);

  /* 移除默认下划线 */
  text-decoration: none;
}

/* 添加渐变下划线动画 */
.task-document-link::before {
  content: '';
  position: absolute;
  width: 0;
  height: 2px;
  bottom: 4px;
  left: 10px;
  background: linear-gradient(90deg, #18a058, #36ad6a);
  transition: width 0.25s ease-in-out;
}

.task-document-link:hover::before {
  width: calc(100% - 20px);
}

/* 点击反馈 */
.task-document-link:active {
  background-color: rgba(24, 160, 88, 0.15);
  transform: translateX(3px) scale(0.98);
  box-shadow: 0 1px 2px rgba(24, 160, 88, 0.12);
}

/* 图标样式（如果有） */
.task-document-link .icon {
  transition: transform 0.2s;
}

.task-document-link:hover .icon {
  transform: scale(1.1);
}

.task-actions {
  display: flex;
  gap: 6px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
}

.mr-2 {
  margin-right: 8px;
}

/* 文档内容样式 */
.document-content {
  padding: 16px;
  background-color: #f9f9f9;
  border-radius: 4px;
  white-space: pre-wrap;
  line-height: 1.6;
  min-height: 200px;
  max-height: 400px;
  overflow-y: auto;
}
</style>

<!-- 现代化任务卡片全局样式 -->
<style>
/* 任务卡片容器 */
.task-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 现代化任务卡片主容器 */
.modern-task-card {
  position: relative;
  display: flex;
  background: #ffffff;
  border-radius: 12px;
  box-shadow:
    0 1px 3px rgba(0, 0, 0, 0.08),
    0 1px 2px rgba(0, 0, 0, 0.04);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  border: 1px solid #f0f0f0;
}

.modern-task-card:hover {
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.12),
    0 4px 8px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
  border-color: #e0e0e0;
}

/* 状态指示条 */
.task-status-indicator {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, var(--status-color) 0%, var(--status-color-light, var(--status-color)) 100%);
}

.task-status-indicator.status-pending {
  --status-color: #94a3b8;
  --status-color-light: #cbd5e1;
}

.task-status-indicator.status-assigned {
  --status-color: var(--color-primary);
  --status-color-light: #93c5fd;
}

.task-status-indicator.status-running {
  --status-color: var(--color-warning);
  --status-color-light: #fbbf24;
}

.task-status-indicator.status-completed {
  --status-color: #10b981;
  --status-color-light: #6ee7b7;
}

.task-status-indicator.status-failed {
  --status-color: var(--color-danger);
  --status-color-light: #f87171;
}

.task-status-indicator.status-blocked {
  --status-color: var(--color-info);
  --status-color-light: #c4b5fd;
}

.task-status-indicator.status-cancelled {
  --status-color: var(--color-text-secondary);
  --status-color-light: var(--color-text-tertiary);
}

/* 卡片主内容区域 */
.task-card-main {
  flex: 1;
  padding: 16px 16px 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 顶部行：状态和类型 */
.task-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.task-left-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 任务编号 */
.task-code {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
  letter-spacing: 0.5px;
}

/* 状态徽章 */
.task-status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.2s ease;
}

.task-status-badge.status-pending {
  background: #f1f5f9;
  color: #64748b;
}

.task-status-badge.status-assigned {
  background: #dbeafe;
  color: var(--color-primary-active);
}

.task-status-badge.status-running {
  background: #fef3c7;
  color: #d97706;
}

.task-status-badge.status-completed {
  background: #d1fae5;
  color: #059669;
}

.task-status-badge.status-failed {
  background: #fee2e2;
  color: #dc2626;
}

.task-status-badge.status-blocked {
  background: #ede9fe;
  color: #7c3aed;
}

.task-status-badge.status-cancelled {
  background: #f3f4f6;
  color: #4b5563;
}

/* 类型徽章 */
.task-type-badge {
  padding: 4px 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #ffffff;
  font-size: 11px;
  font-weight: 600;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
}

/* 任务标题 */
.task-title-heading {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
  letter-spacing: -0.01em;
}

/* 任务描述 */
.task-description {
  color: #64748b;
  line-height: 1.6;
  font-size: 14px;
}

.task-description p:last-child {
  margin-bottom: 0;
}

/* 文档区域 */
.task-documents-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.task-documents-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.document-icon,
.subtasks-icon {
  font-size: 16px;
  color: #64748b;
  vertical-align: middle;
}

.task-documents-count {
  background: #e2e8f0;
  color: #475569;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.task-document-links {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-document-link {
  color: #0891b2;
  text-decoration: none;
  font-size: 13px;
  padding: 6px 10px;
  border-radius: 6px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  font-weight: 500;
  border: 1px solid transparent;
  position: relative;
}

.task-document-link::before {
  content: '📄';
  margin-right: 6px;
  font-size: 12px;
}

.task-document-link:hover {
  background: #ecfeff;
  color: #0e7490;
  border-color: #cbd5e1;
  transform: translateX(4px);
  box-shadow: 0 2px 4px rgba(8, 145, 178, 0.1);
}

/* 子任务区域 */
.subtasks-section {
  margin-top: 4px;
  padding: 12px;
  background: #fefce8;
  border-radius: 8px;
  border: 1px solid #fef08a;
}

.subtasks-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #854d0e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.subtasks-collapse :deep(.n-collapse-item) {
  background: transparent;
  border: none;
}

.subtasks-collapse :deep(.n-collapse-item__header) {
  padding: 0;
  font-size: 13px;
  font-weight: 500;
  color: #713f12;
}

/* 操作栏 */
.task-actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  margin-top: 4px;
}

.task-primary-actions {
  display: flex;
  gap: 8px;
}

.task-secondary-actions {
  display: flex;
  gap: 4px;
}

/* MarkdownRenderer 在任务卡片中的样式覆盖 */
.task-card-main .markdown-body {
  color: #64748b;
}
</style>
