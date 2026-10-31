<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { NButton, NSpace, NTabPane, NTabs, NTag, NText } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import {
  getRequirementPriorityTagType,
  getRequirementStatusTagType,
  requirementPriorityOptions,
  requirementStatusOptions
} from '@/constants/requirement';
import { fetchProjectList } from '@/service/api';
import { useRequirementStore } from '@/store/modules/requirement';
import { useAuthStore } from '@/store/modules/auth';
import type { Api } from '@/typings/api';

defineOptions({
  name: 'Requirements'
});

const requirementStore = useRequirementStore();
const authStore = useAuthStore();
const router = useRouter();

const requirements = ref<Api.Requirement.Requirement[]>([]);
const allRequirements = ref<Api.Requirement.Requirement[]>([]); // 保存所有需求，用于 tab 切换
const loading = ref(false);

// 获取当前用户 ID
const currentUserId = computed(() => authStore.userInfo?.userId || '');

// Tab 状态
const activeTab = ref<'my_todo' | 'open' | 'closed' | 'all'>('open');
const showCreateModal = ref(false);
const showEditModal = ref(false);
const currentRequirement = ref<Api.Requirement.Requirement | null>(null);
const projects = ref<Api.Project.Project[]>([]);
const projectsLoading = ref(false);

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 30, 50]
});

// Filters
const filters = reactive({
  status: undefined as string | undefined,
  priority: undefined as Api.Requirement.Priority | undefined,
  project_id: undefined as string | undefined
});

// Form data
const formData = reactive({
  title: '',
  description: '',
  priority: undefined as Api.Requirement.Priority | undefined,
  tags: [] as string[],
  project_id: undefined as string | undefined
});

// Use imported constants and utility functions
const statusOptions = requirementStatusOptions;
const priorityOptions = requirementPriorityOptions;
const getStatusType = getRequirementStatusTagType;
const getPriorityType = getRequirementPriorityTagType;

// Tab 统计
const tabCounts = computed(() => {
  const openStatuses: Api.Requirement.RequirementStatus[] = ['planning', 'generating'];
  const closedStatuses: Api.Requirement.RequirementStatus[] = ['completed', 'closed'];

  // 应用其他 filters（不包括 status）
  let base = [...allRequirements.value];
  if (filters.priority) {
    base = base.filter(requirement => requirement.priority === filters.priority);
  }
  if (filters.project_id) {
    base = base.filter(requirement => requirement.project_id === filters.project_id);
  }

  return {
    my_todo: base.filter(
      requirement => requirement.assignee_id === currentUserId.value && openStatuses.includes(requirement.status)
    ).length,
    open: base.filter(requirement => openStatuses.includes(requirement.status)).length,
    closed: base.filter(requirement => closedStatuses.includes(requirement.status)).length,
    all: base.length
  };
});

// Load requirements
async function loadRequirements() {
  loading.value = true;
  try {
    // 获取所有页的数据用于统计和前端分页
    allRequirements.value = [];
    const fetchedRequirements: Api.Requirement.Requirement[] = [];
    let page = 1;
    let hasMore = true;

    /* eslint-disable no-await-in-loop */
    while (hasMore) {
      await requirementStore.getRequirements({
        priority: filters.priority,
        project_id: filters.project_id,
        page,
        page_size: 100
      });

      if (requirementStore.requirements) {
        fetchedRequirements.push(...requirementStore.requirements);

        // 如果当前页数据少于 page_size，说明已经是最后一页
        hasMore = requirementStore.requirements.length === 100;
        page += 1;
      } else {
        hasMore = false;
      }
    }
    /* eslint-enable no-await-in-loop */

    allRequirements.value = fetchedRequirements;

    // 应用过滤和分页
    applyTabAndFilters();
  } finally {
    loading.value = false;
  }
}

// 根据 tab 和 filters 过滤 requirements
function applyTabAndFilters() {
  let filtered = [...allRequirements.value];

  // 应用 tab 过滤
  if (activeTab.value === 'my_todo') {
    // 我的待办：分配给当前用户且未关闭的需求
    const openStatuses: Api.Requirement.RequirementStatus[] = ['planning', 'generating'];
    filtered = filtered.filter(
      requirement => requirement.assignee_id === currentUserId.value && openStatuses.includes(requirement.status)
    );
  } else if (activeTab.value === 'open') {
    const openStatuses: Api.Requirement.RequirementStatus[] = ['planning', 'generating'];
    filtered = filtered.filter(requirement => openStatuses.includes(requirement.status));
  } else if (activeTab.value === 'closed') {
    const closedStatuses: Api.Requirement.RequirementStatus[] = ['completed', 'closed'];
    filtered = filtered.filter(requirement => closedStatuses.includes(requirement.status));
  }
  // 'all' 不过滤

  // 应用其他 filters（除了 status，因为 status 由 tab 控制）
  if (filters.priority) {
    filtered = filtered.filter(requirement => requirement.priority === filters.priority);
  }
  if (filters.project_id) {
    filtered = filtered.filter(requirement => requirement.project_id === filters.project_id);
  }

  // 更新分页总数
  pagination.itemCount = filtered.length;

  // 应用分页：只取当前页的数据
  const start = (pagination.page - 1) * pagination.pageSize;
  const end = start + pagination.pageSize;
  requirements.value = filtered.slice(start, end);
}

// 处理页码变化
function handlePageChange(page: number) {
  pagination.page = page;
  applyTabAndFilters(); // 前端分页
}

// 处理每页数量变化
function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize;
  pagination.page = 1; // 重置到第一页
  applyTabAndFilters(); // 前端分页
}

// Load projects
async function loadProjects() {
  projectsLoading.value = true;
  try {
    const response = await fetchProjectList();
    projects.value = response.data || [];
  } catch (error) {
    console.error('Failed to load projects:', error);
    projects.value = [];
  } finally {
    projectsLoading.value = false;
  }
}

// Create requirement
async function handleCreate() {
  try {
    if (!formData.project_id) {
      window.$message?.error('请选择项目');
      return;
    }

    await requirementStore.addRequirement({
      title: formData.title,
      description: formData.description,
      priority: formData.priority,
      tags: formData.tags,
      project_id: formData.project_id
      // created_by 由后端以认证身份写入，不再由前端传递
    });
    showCreateModal.value = false;
    resetForm();
    await loadRequirements();
    window.$message?.success('需求创建成功');
  } catch {
    window.$message?.error('需求创建失败');
  }
}

// Edit requirement
async function handleEdit() {
  if (!currentRequirement.value) return;
  try {
    const updateData: Api.Requirement.UpdateRequirement = {
      title: formData.title,
      description: formData.description,
      priority: formData.priority
    };
    // 只有当 project_id 有值时才传递
    if (formData.project_id !== undefined) {
      updateData.project_id = formData.project_id;
    }
    await requirementStore.editRequirement(currentRequirement.value.id, updateData);
    showEditModal.value = false;
    resetForm();
    await loadRequirements();
    window.$message?.success('需求更新成功');
  } catch {
    window.$message?.error('需求更新失败');
  }
}

// Delete requirement
function handleDelete(requirement: Api.Requirement.Requirement) {
  window.$dialog?.warning({
    title: '确认删除',
    content: `确定要删除需求 "${requirement.title}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await requirementStore.removeRequirement(requirement.id);
        await loadRequirements();
        window.$message?.success('需求删除成功');
      } catch {
        window.$message?.error('需求删除失败');
      }
    }
  });
}

// View requirement detail
function viewRequirement(requirement: Api.Requirement.Requirement) {
  router.push({
    path: '/workflow/requirement-detail',
    query: { id: requirement.id }
  });
}

// Open create modal
function openCreateModal() {
  resetForm();
  // 预选当前筛选的项目
  if (filters.project_id) {
    formData.project_id = filters.project_id;
  }
  showCreateModal.value = true;
}

// Open edit modal
function openEditModal(requirement: Api.Requirement.Requirement) {
  currentRequirement.value = requirement;
  formData.title = requirement.title;
  formData.description = requirement.description || '';
  formData.priority = requirement.priority || undefined;
  // 设置当前项目（如果有）
  formData.project_id = (requirement as any).project_id || undefined;
  showEditModal.value = true;
}

// Reset form
function resetForm() {
  formData.title = '';
  formData.description = '';
  formData.priority = undefined;
  formData.tags = [];
  formData.project_id = undefined;
  currentRequirement.value = null;
}

// Handle filter change
async function handleFilterChange() {
  // 筛选条件改变后，重新获取所有数据
  pagination.page = 1; // 重置到第一页
  await loadRequirements();
}

// Handle tab change
function handleTabChange(tab: 'my_todo' | 'open' | 'closed' | 'all') {
  activeTab.value = tab;
  applyTabAndFilters();
}

// Table columns
const columns: DataTableColumns<Api.Requirement.Requirement> = [
  {
    title: '需求编号',
    key: 'code',
    width: 120
  },
  {
    title: '需求标题',
    key: 'title',
    width: 250,
    ellipsis: { tooltip: true }
  },
  {
    title: '描述',
    key: 'description',
    width: 300,
    ellipsis: { tooltip: true },
    render: row => row.description || '无描述'
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    render: row => {
      const label = statusOptions.find(s => s.value === row.status)?.label || row.status;
      return h(NTag, { type: getStatusType(row.status), size: 'small' }, { default: () => label });
    }
  },
  {
    title: '优先级',
    key: 'priority',
    width: 100,
    render: row => {
      if (!row.priority) return '-';
      const label = priorityOptions.find(p => p.value === row.priority)?.label;
      return h(NTag, { type: getPriorityType(row.priority), size: 'small' }, { default: () => label });
    }
  },
  // {
  //   title: '标签',
  //   key: 'tags',
  //   width: 150,
  //   render: row => renderTags(row.tags || [])
  // },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 150,
    render: row =>
      h(NText, { depth: 3, style: { fontSize: '12px' } }, { default: () => new Date(row.updated_at).toLocaleString() })
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    fixed: 'right' as const,
    render: row =>
      h(NSpace, null, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => viewRequirement(row) }, { default: () => '详情' }),
          h(NButton, { size: 'small', onClick: () => openEditModal(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row) }, { default: () => '删除' })
        ]
      })
  }
];

// Project options
const projectOptions = computed(() => {
  const options = [
    {
      label: '未归类',
      value: ''
    },
    ...projects.value.map(p => ({
      label: p.name,
      value: p.id
    }))
  ];
  return options;
});

onMounted(() => {
  loadProjects();
  loadRequirements();
});
</script>

<template>
  <div class="requirements-container">
    <NCard :bordered="false">
      <template #header>
        <NSpace align="center" justify="space-between" style="width: 100%">
          <NText strong style="font-size: 16px">需求管理</NText>
          <NButton type="primary" @click="openCreateModal">
            <template #icon>
              <icon-mdi-plus />
            </template>
            新建需求
          </NButton>
        </NSpace>
      </template>

      <!-- Tabs and Filters -->
      <div class="tabs-and-filters">
        <!-- Tabs -->
        <div class="tabs-section">
          <NTabs v-model:value="activeTab" type="line" size="small" @update:value="handleTabChange">
            <NTabPane name="my_todo">
              <template #tab>
                <div class="tab-content">
                  <icon-mdi-account-check class="tab-icon" />
                  <span class="tab-label">我的待办</span>
                  <span class="tab-count" :class="{ 'tab-count-active': activeTab === 'my_todo' }">
                    {{ tabCounts.my_todo }}
                  </span>
                </div>
              </template>
            </NTabPane>
            <NTabPane name="open">
              <template #tab>
                <div class="tab-content">
                  <icon-mdi-lock-open class="tab-icon" />
                  <span class="tab-label">开放中</span>
                  <span class="tab-count" :class="{ 'tab-count-active': activeTab === 'open' }">
                    {{ tabCounts.open }}
                  </span>
                </div>
              </template>
            </NTabPane>
            <NTabPane name="closed">
              <template #tab>
                <div class="tab-content">
                  <icon-mdi-check-circle class="tab-icon" />
                  <span class="tab-label">已关闭</span>
                  <span class="tab-count" :class="{ 'tab-count-active': activeTab === 'closed' }">
                    {{ tabCounts.closed }}
                  </span>
                </div>
              </template>
            </NTabPane>
            <NTabPane name="all">
              <template #tab>
                <div class="tab-content">
                  <icon-mdi-format-list-bulleted class="tab-icon" />
                  <span class="tab-label">全部</span>
                  <span class="tab-count" :class="{ 'tab-count-active': activeTab === 'all' }">
                    {{ tabCounts.all }}
                  </span>
                </div>
              </template>
            </NTabPane>
          </NTabs>
        </div>

        <!-- Filters -->
        <div class="filters-row">
          <NSelect
            v-model:value="filters.project_id"
            :options="projectOptions"
            placeholder="全部项目"
            clearable
            :loading="projectsLoading"
            style="width: 200px"
            @update:value="handleFilterChange"
          />
          <NSelect
            v-model:value="filters.priority"
            :options="priorityOptions"
            placeholder="筛选优先级"
            clearable
            style="width: 150px"
            @update:value="handleFilterChange"
          />
        </div>
      </div>

      <NSpin :show="loading">
        <NEmpty v-if="!loading && requirements.length === 0" description="暂无需求" size="large" />
        <NDataTable
          v-else
          :columns="columns"
          :data="requirements"
          :row-key="(row: Api.Requirement.Requirement) => row.id"
          :scroll-x="1400"
          striped
          size="small"
        />
        <div v-if="requirements.length > 0" class="pagination-wrapper">
          <NPagination
            v-model:page="pagination.page"
            :page-size="pagination.pageSize"
            :item-count="pagination.itemCount"
            :page-sizes="pagination.pageSizes"
            show-size-picker
            @update:page="handlePageChange"
            @update:page-size="handlePageSizeChange"
          />
        </div>
      </NSpin>
    </NCard>

    <!-- Create Modal -->
    <NModal v-model:show="showCreateModal" preset="card" title="新建需求" style="width: 600px">
      <NForm ref="formRef" :model="formData" label-placement="left" label-width="80">
        <NFormItem label="所属项目" path="project_id" :rule="{ required: true, message: '请选择所属项目' }">
          <NSelect
            v-model:value="formData.project_id"
            :options="projectOptions"
            placeholder="请选择所属项目"
            :loading="projectsLoading"
          />
        </NFormItem>
        <NFormItem label="需求标题" path="title" :rule="{ required: true, message: '请输入需求标题' }">
          <NInput v-model:value="formData.title" placeholder="请输入需求标题" />
        </NFormItem>
        <NFormItem label="需求描述" path="description">
          <NInput
            v-model:value="formData.description"
            type="textarea"
            placeholder="请输入需求描述（可选）"
            :autosize="{ minRows: 3, maxRows: 6 }"
          />
        </NFormItem>
        <NFormItem label="优先级" path="priority">
          <NSelect v-model:value="formData.priority" :options="priorityOptions" placeholder="选择优先级" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCreateModal = false">取消</NButton>
          <NButton type="primary" @click="handleCreate">创建</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Edit Modal -->
    <NModal v-model:show="showEditModal" preset="card" title="编辑需求" style="width: 600px">
      <NForm ref="formRef" :model="formData" label-placement="left" label-width="80">
        <NFormItem label="所属项目" path="project_id">
          <NSelect
            v-model:value="formData.project_id"
            :options="projectOptions"
            placeholder="请选择所属项目（留空则不修改）"
            :loading="projectsLoading"
            clearable
          />
        </NFormItem>
        <NFormItem label="需求标题" path="title" :rule="{ required: true, message: '请输入需求标题' }">
          <NInput v-model:value="formData.title" placeholder="请输入需求标题" />
        </NFormItem>
        <NFormItem label="需求描述" path="description">
          <NInput
            v-model:value="formData.description"
            type="textarea"
            placeholder="请输入需求描述（可选）"
            :autosize="{ minRows: 3, maxRows: 6 }"
          />
        </NFormItem>
        <NFormItem label="优先级" path="priority">
          <NSelect v-model:value="formData.priority" :options="priorityOptions" placeholder="选择优先级" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showEditModal = false">取消</NButton>
          <NButton type="primary" @click="handleEdit">保存</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Requirement Drawer -->
  </div>
</template>

<style scoped>
.requirements-container {
  padding: 16px;
}

/* Tabs and Filters 容器 */
.tabs-and-filters {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  margin-bottom: 0;
}

/* Tabs 区域 */
.tabs-section {
  padding: 0 16px;
  border-bottom: 1px solid #e8eaed;
}

.tabs-section :deep(.n-tabs-nav) {
  padding: 0;
}

.tabs-section :deep(.n-tabs-tab) {
  padding: 10px 16px;
  font-size: 13px;
}

.tabs-section :deep(.n-tabs-tab--active) {
  font-weight: 600;
}

.tab-content {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-icon {
  font-size: 16px;
  opacity: 0.6;
  transition: all 0.2s;
}

.tabs-section :deep(.n-tabs-tab--active) .tab-icon {
  opacity: 1;
}

.tab-label {
  font-size: 13px;
}

.tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 18px;
  padding: 0 6px;
  font-size: 11px;
  font-weight: 600;
  color: #909399;
  background: var(--color-bg-tertiary);
  border-radius: 9px;
  transition: all 0.2s;
}

.tab-count-active {
  color: white;
  background: #18a058;
}

/* 筛选行 */
.filters-row {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background: #fafbfc;
  border-bottom: 1px solid #e8eaed;
}

/* 分页组件样式 */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  background: white;
  border-top: 1px solid #e8eaed;
}

.pagination-wrapper :deep(.n-pagination) {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-wrapper :deep(.n-pagination-item) {
  border-radius: 4px;
  font-size: 13px;
}

.pagination-wrapper :deep(.n-pagination-item--active) {
  background: #18a058;
  border-color: #18a058;
  color: white;
}

.pagination-wrapper :deep(.n-pagination-item:hover:not(.n-pagination-item--disabled)) {
  border-color: #18a058;
  color: #18a058;
}
</style>
