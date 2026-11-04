<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NDataTable,
  NDropdown,
  NEmpty,
  NInput,
  NModal,
  NPagination,
  NSelect,
  NSpace,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  NText,
  NTooltip
} from 'naive-ui';
import type { DataTableColumns, DropdownOption } from 'naive-ui';
import {
  getIssuePriorityTagType,
  getIssueStatusTagType,
  getIssueTypeTagType,
  issuePriorityOptions,
  issueStatusOptions,
  issueTypeOptions
} from '@/constants/issue';
import { fetchProjectList } from '@/service/api';
import { issueApi } from '@/service/api/issue';
import {
  type SavedView,
  fetchCreateSavedView,
  fetchSavedViews,
  fetchSetSavedViewFavorite,
  fetchUpdateSavedView
} from '@/service/api/saved-views';
import { useIssueStore } from '@/store/modules/issue';
import { useAuthStore } from '@/store/modules/auth';
import { GROUP_BY_OPTIONS, type GroupByKey, isGroupByKey } from '@/utils/groupIssuesBy';
import type { ParsedQuery } from '@/utils/issueSearchParser';
import IssueSmartSearch from '@/components/IssueSmartSearch.vue';
import type { Api } from '@/typings/api';
import IssueBoard from './modules/IssueBoard.vue';
import IssueListGrouped from './modules/IssueListGrouped.vue';

defineOptions({
  name: 'IssueList'
});

const issueStore = useIssueStore();
const authStore = useAuthStore();
const router = useRouter();

const issues = ref<Api.Issue.Issue[]>([]);
const allIssues = ref<Api.Issue.Issue[]>([]); // 保存所有 issue，用于 tab 切换
const loading = ref(false);
const projects = ref<Api.Project.Project[]>([]);
const projectsLoading = ref(false);

// 获取当前用户 ID
const currentUserId = computed(() => authStore.userInfo?.userId || '');

// 分页状态
const pagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100]
});

// Tab 状态
const activeTab = ref<'my_issues' | 'open' | 'closed' | 'all'>('open');

// 双视图：list | board（同数据源）
const viewMode = ref<'list' | 'board'>('list');
const filteredIssues = ref<Api.Issue.Issue[]>([]);

/** E4-S2：列表分组依据（本地状态；可写入 Saved View display.group_by） */
const groupBy = ref<GroupByKey>('none');
const groupByOptions = GROUP_BY_OPTIONS;

const isGroupedList = computed(() => groupBy.value !== 'none');
const activeGroupBy = computed(() => groupBy.value as Exclude<GroupByKey, 'none'>);

// 筛选框展开状态（默认关闭）
const filtersExpanded = ref(false);

// Filters
const filters = reactive({
  status: undefined as Api.Issue.IssueStatus | undefined,
  priority: undefined as Api.Issue.IssuePriority | undefined,
  type: undefined as Api.Issue.IssueType | undefined,
  project_id: undefined as string | undefined,
  search: ''
});

// 智能搜索
const smartSearchValue = ref('');

// Saved Views（E4-S1 个人视图）
const savedViews = ref<SavedView[]>([]);
const savedViewsLoading = ref(false);
const saveViewModalVisible = ref(false);
const saveViewName = ref('');
const saveViewSubmitting = ref(false);
const activeSavedViewId = ref<string | null>(null);

async function loadSavedViews() {
  savedViewsLoading.value = true;
  try {
    const response = await fetchSavedViews();
    savedViews.value = response.data?.rows || [];
  } catch {
    savedViews.value = [];
  } finally {
    savedViewsLoading.value = false;
  }
}

function buildCurrentFilterPayload() {
  const filter: Record<string, unknown> = {};
  if (filters.status) filter.status = filters.status;
  if (filters.type) filter.type = filters.type;
  if (filters.priority) filter.priority = filters.priority;
  if (filters.project_id) filter.project_id = filters.project_id;
  if (filters.search) filter.search = filters.search;
  filter.tab = activeTab.value;
  return filter;
}

function openSaveViewModal() {
  saveViewName.value = '';
  saveViewModalVisible.value = true;
}

async function confirmSaveView() {
  const name = saveViewName.value.trim();
  if (!name) {
    window.$message?.warning('请输入视图名称');
    return false;
  }
  saveViewSubmitting.value = true;
  try {
    await fetchCreateSavedView({
      name,
      filter: buildCurrentFilterPayload(),
      sort: { sort_by: 'created_at', sort_order: 'desc' },
      display: { view_mode: viewMode.value, group_by: groupBy.value },
      is_favorite: false
    });
    window.$message?.success('视图已保存');
    await loadSavedViews();
    return true;
  } catch {
    window.$message?.error('保存视图失败');
    return false;
  } finally {
    saveViewSubmitting.value = false;
  }
}

async function applySavedView(view: SavedView) {
  const f = view.filter || {};
  filters.type = (f.type as Api.Issue.IssueType | undefined) || undefined;
  filters.priority = (f.priority as Api.Issue.IssuePriority | undefined) || undefined;
  filters.project_id = (f.project_id as string | undefined) || undefined;
  filters.status = (f.status as Api.Issue.IssueStatus | undefined) || undefined;
  filters.search = (f.search as string | undefined) || '';
  smartSearchValue.value = filters.search || '';

  const tab = (f.tab as 'my_issues' | 'open' | 'closed' | 'all' | undefined) || undefined;
  if (tab) {
    activeTab.value = tab;
  } else if (filters.status) {
    const openStatuses: Api.Issue.IssueStatus[] = ['open', 'in_progress', 'feedback'];
    const closedStatuses: Api.Issue.IssueStatus[] = ['closed', 'rejected', 'resolved'];
    if (openStatuses.includes(filters.status)) activeTab.value = 'open';
    else if (closedStatuses.includes(filters.status)) activeTab.value = 'closed';
  }

  if (view.display?.view_mode === 'board' || view.display?.view_mode === 'list') {
    viewMode.value = view.display.view_mode;
  }
  if (isGroupByKey(view.display?.group_by)) {
    groupBy.value = view.display.group_by;
  } else {
    groupBy.value = 'none';
  }

  activeSavedViewId.value = view.id;
  pagination.page = 1;
  await loadIssues();
  window.$message?.success(`已应用视图「${view.name}」`);
}

async function toggleActiveViewFavorite() {
  const id = activeSavedViewId.value;
  if (!id) {
    window.$message?.info('请先应用一个已保存视图');
    return;
  }
  const view = savedViews.value.find(v => v.id === id);
  if (!view) return;
  try {
    await fetchSetSavedViewFavorite(view.id, !view.isFavorite);
    await loadSavedViews();
    window.$message?.success(view.isFavorite ? '已取消收藏' : '已收藏');
  } catch {
    window.$message?.error('更新收藏失败');
  }
}

const savedViewDropdownOptions = computed<DropdownOption[]>(() => {
  if (!savedViews.value.length) {
    return [{ label: '暂无已保存视图', key: '__empty', disabled: true }];
  }
  return savedViews.value.map(v => ({
    label: v.isFavorite ? `★ ${v.name}` : v.name,
    key: v.id
  }));
});

function handleSavedViewSelect(key: string | number) {
  const id = String(key);
  if (id === '__empty') return;
  const view = savedViews.value.find(v => v.id === id);
  if (view) {
    applySavedView(view);
  }
}

// 语法帮助显示状态
const showSyntaxHelp = ref(false);

// 语法说明示例
const syntaxExamples = [
  { text: 'assignee:@me', desc: '显示分配给我的 Issue' },
  { text: 'is:open', desc: '只显示待办中的 Issue' },
  { text: 'is:closed', desc: '只显示已完成的 Issue' },
  { text: 'is:in_progress', desc: '只显示进行中的 Issue' },
  { text: 'type:feature', desc: '只显示功能类型的 Issue' },
  { text: 'type:bug', desc: '只显示缺陷类型的 Issue' },
  { text: 'priority:urgent', desc: '只显示紧急优先级的 Issue' },
  { text: 'priority:high', desc: '只显示高优先级的 Issue' }
];

// Load issues
async function loadIssues() {
  loading.value = true;
  try {
    // 获取所有页的数据用于统计和前端分页
    allIssues.value = [];
    const fetchedIssues: Api.Issue.Issue[] = [];
    let page = 1;
    let hasMore = true;

    /* eslint-disable no-await-in-loop */
    while (hasMore) {
      const response = await issueApi.getIssues({
        page,
        page_size: 100,
        priority: filters.priority,
        type: filters.type,
        project_id: filters.project_id,
        search: filters.search || undefined
      });

      if (response.data?.rows) {
        fetchedIssues.push(...response.data.rows);

        // 如果当前页数据少于 page_size，说明已经是最后一页
        hasMore = response.data.rows.length === 100;
        page += 1;
      } else {
        hasMore = false;
      }
    }
    /* eslint-enable no-await-in-loop */

    allIssues.value = fetchedIssues;

    // 应用过滤和分页
    applyTabAndFilters();
  } finally {
    loading.value = false;
  }
}

// 根据 tab 和 filters 过滤 issues
function applyTabAndFilters() {
  let filtered = [...allIssues.value];

  // 应用 tab 过滤
  if (activeTab.value === 'my_issues') {
    // 我的待办：分配给当前用户且未关闭的问题
    const openStatuses: Api.Issue.IssueStatus[] = ['open', 'in_progress', 'feedback'];
    filtered = filtered.filter(
      issue => issue.assignee_id === currentUserId.value && openStatuses.includes(issue.status)
    );
  } else if (activeTab.value === 'open') {
    const openStatuses: Api.Issue.IssueStatus[] = ['open', 'in_progress', 'feedback'];
    filtered = filtered.filter(issue => openStatuses.includes(issue.status));
  } else if (activeTab.value === 'closed') {
    const closedStatuses: Api.Issue.IssueStatus[] = ['closed', 'rejected', 'resolved'];
    filtered = filtered.filter(issue => closedStatuses.includes(issue.status));
  }
  // 'all' 不过滤

  // 应用其他 filters（除了 status，因为 status 由 tab 控制）
  if (filters.type) {
    filtered = filtered.filter(issue => issue.type === filters.type);
  }
  if (filters.priority) {
    filtered = filtered.filter(issue => issue.priority === filters.priority);
  }
  if (filters.project_id) {
    filtered = filtered.filter(issue => issue.project_id === filters.project_id);
  }
  if (filters.search) {
    const searchLower = filters.search.toLowerCase();
    filtered = filtered.filter(
      issue => issue.title.toLowerCase().includes(searchLower) || issue.issue_code.toLowerCase().includes(searchLower)
    );
  }

  // 更新分页总数与看板全量（未分页）
  filteredIssues.value = filtered;
  pagination.itemCount = filtered.length;

  // 应用分页：只取当前页的数据（列表视图）
  const start = (pagination.page - 1) * pagination.pageSize;
  const end = start + pagination.pageSize;
  issues.value = filtered.slice(start, end);
}

// 处理智能搜索
async function handleSmartSearch(query: ParsedQuery) {
  // 根据 status 切换 tab
  if (query.status) {
    const status = query.status as Api.Issue.IssueStatus;
    const openStatuses: Api.Issue.IssueStatus[] = ['open', 'in_progress', 'feedback'];
    const closedStatuses: Api.Issue.IssueStatus[] = ['closed', 'rejected', 'resolved'];

    if (openStatuses.includes(status)) {
      activeTab.value = 'open';
    } else if (closedStatuses.includes(status)) {
      activeTab.value = 'closed';
    } else {
      activeTab.value = 'all';
    }
  }

  // 更新其他 filters
  if (query.type) {
    filters.type = query.type as Api.Issue.IssueType;
  } else {
    filters.type = undefined;
  }

  if (query.priority) {
    filters.priority = query.priority as Api.Issue.IssuePriority;
  } else {
    filters.priority = undefined;
  }

  if (query.project_id) {
    filters.project_id = query.project_id;
  } else {
    filters.project_id = undefined;
  }

  // 处理搜索词（包括普通搜索和特殊过滤器）
  const searchParts: string[] = [];
  if (query.search) {
    searchParts.push(query.search);
  }

  // 将 assignee 和 creator 添加到搜索中（因为 API 可能不支持这些字段）
  if (query.assignee_id) {
    searchParts.push(`assignee:${query.assignee_id}`);
    // 如果搜索的是分配给当前用户的问题，切换到"我的待办"tab
    if (query.assignee_id === currentUserId.value) {
      activeTab.value = 'my_issues';
    }
  }
  if (query.reporter_id) {
    searchParts.push(`author:${query.reporter_id}`);
  }

  filters.search = searchParts.join(' ') || '';

  // 搜索条件改变后，重新获取所有数据
  pagination.page = 1; // 重置到第一页
  await loadIssues();
}

// Use imported constants and utility functions
const statusOptions = issueStatusOptions;
const priorityOptions = issuePriorityOptions;
const typeOptions = issueTypeOptions;
const getStatusType = getIssueStatusTagType;
const getPriorityType = getIssuePriorityTagType;
const getTypeType = getIssueTypeTagType;

// Load projects
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

// Tab 统计
const tabCounts = computed(() => {
  const openStatuses: Api.Issue.IssueStatus[] = ['open', 'in_progress', 'feedback'];
  const closedStatuses: Api.Issue.IssueStatus[] = ['closed', 'rejected', 'resolved'];

  // 应用其他 filters（不包括 status）
  let base = [...allIssues.value];
  if (filters.type) {
    base = base.filter(issue => issue.type === filters.type);
  }
  if (filters.priority) {
    base = base.filter(issue => issue.priority === filters.priority);
  }
  if (filters.project_id) {
    base = base.filter(issue => issue.project_id === filters.project_id);
  }
  if (filters.search) {
    const searchLower = filters.search.toLowerCase();
    base = base.filter(
      issue => issue.title.toLowerCase().includes(searchLower) || issue.issue_code.toLowerCase().includes(searchLower)
    );
  }

  return {
    my_issues: base.filter(issue => issue.assignee_id === currentUserId.value && openStatuses.includes(issue.status))
      .length,
    open: base.filter(issue => openStatuses.includes(issue.status)).length,
    closed: base.filter(issue => closedStatuses.includes(issue.status)).length,
    all: base.length
  };
});

// Delete issue
function handleDelete(issue: Api.Issue.Issue) {
  window.$dialog?.warning({
    title: '确认删除',
    content: `确定要删除 Issue "${issue.title}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await issueStore.deleteIssue(issue.id);
        await loadIssues();
        window.$message?.success('Issue 删除成功');
      } catch {
        window.$message?.error('Issue 删除失败');
      }
    }
  });
}

// View issue detail
function viewIssue(issue: Api.Issue.Issue) {
  router.push({
    path: '/issue/detail',
    query: { id: issue.id }
  });
}

// Create new issue
function createIssue() {
  router.push({
    path: '/issue/create'
  });
}

// Handle filter change
async function handleFilterChange() {
  // 筛选条件改变后，重新获取所有数据
  pagination.page = 1; // 重置到第一页
  await loadIssues();
}

// Handle tab change
function handleTabChange(tab: 'my_issues' | 'open' | 'closed' | 'all') {
  activeTab.value = tab;
  applyTabAndFilters();
}

// Handle page change
function handlePageChange(page: number) {
  pagination.page = page;
  applyTabAndFilters(); // 前端分页
}

// Handle page size change
function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize;
  pagination.page = 1; // 重置到第一页
  applyTabAndFilters(); // 前端分页
}

async function handleGroupByChange(value: GroupByKey | null) {
  groupBy.value = value || 'none';
  const id = activeSavedViewId.value;
  if (!id) return;
  try {
    await fetchUpdateSavedView(id, {
      display: { view_mode: viewMode.value, group_by: groupBy.value }
    });
    await loadSavedViews();
  } catch {
    window.$message?.warning('分组已切换，但同步到已保存视图失败');
  }
}

// Clear all filters
function clearFilters() {
  filters.project_id = undefined;
  filters.type = undefined;
  filters.status = undefined;
  filters.priority = undefined;
  filters.search = '';
  smartSearchValue.value = '';
  applyTabAndFilters();
}

// Computed: Check if any filters are active
const hasActiveFilters = computed(() => {
  return Boolean(filters.project_id || filters.type || filters.status || filters.priority || filters.search);
});

// Get project name by id
function getProjectName(projectId: string): string {
  const project = projects.value.find(p => p.id === projectId);
  return project?.name || projectId;
}

// Get type label
function getTypeLabel(type: Api.Issue.IssueType): string {
  const option = typeOptions.find(opt => opt.value === type);
  return option?.label || type;
}

// Get status label (reserved for future use)
// function getStatusLabel(status: Api.Issue.IssueStatus): string {
//   const option = statusOptions.find(opt => opt.value === status);
//   return option?.label || status;
// }

// Get priority label
function getPriorityLabel(priority: Api.Issue.IssuePriority): string {
  const option = priorityOptions.find(opt => opt.value === priority);
  return option?.label || priority;
}

// Table columns
const columns: DataTableColumns<Api.Issue.Issue> = [
  {
    title: '编号',
    key: 'issue_code',
    width: 120,
    ellipsis: { tooltip: true }
  },
  {
    title: '标题',
    key: 'title',
    width: 300,
    ellipsis: { tooltip: true }
  },
  {
    title: '类型',
    key: 'type',
    width: 100,
    render: row => {
      const label = typeOptions.find(t => t.value === row.type)?.label || row.type;
      return h(NTag, { type: getTypeType(row.type), size: 'small' }, { default: () => label });
    }
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
      const label = priorityOptions.find(p => p.value === row.priority)?.label;
      return h(NTag, { type: getPriorityType(row.priority), size: 'small' }, { default: () => label || '-' });
    }
  },
  {
    title: '负责人',
    key: 'assignee_id',
    width: 120,
    render: row => {
      if (row.assignee) {
        return row.assignee.name || row.assignee.id;
      }
      return '-';
    }
  },
  {
    title: '报告人',
    key: 'reporter_id',
    width: 120,
    render: row => {
      if (row.reporter) {
        return row.reporter.name || row.reporter.id;
      }
      if (row.created_by === 'system') {
        return '系统';
      }
      return '-';
    }
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 150,
    render: row => {
      const date = new Date(row.created_at);
      const dateStr = date.toLocaleDateString();
      const timeStr = date.toTimeString().slice(0, 5); // HH:MM，去掉秒
      return h(NText, { depth: 3, style: { fontSize: '12px' } }, { default: () => `${dateStr} ${timeStr}` });
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    fixed: 'right' as const,
    render: row =>
      h(NSpace, null, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => viewIssue(row) }, { default: () => '详情' }),
          h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row) }, { default: () => '删除' })
        ]
      })
  }
];

// Project options
const projectOptions = computed(() => {
  return projects.value.map(p => ({
    label: p.name,
    value: p.id
  }));
});

onMounted(() => {
  loadProjects();
  loadIssues();
  loadSavedViews();
});
</script>

<template>
  <div class="issue-list-container">
    <NCard :bordered="false">
      <template #header>
        <NSpace align="center" justify="space-between" style="width: 100%">
          <NText strong style="font-size: 16px">Issue 管理</NText>
          <NSpace align="center">
            <NButton
              size="small"
              :type="viewMode === 'list' ? 'primary' : 'default'"
              secondary
              @click="viewMode = 'list'"
            >
              <template #icon>
                <icon-mdi-view-list />
              </template>
              列表
            </NButton>
            <NButton
              size="small"
              :type="viewMode === 'board' ? 'primary' : 'default'"
              secondary
              @click="viewMode = 'board'"
            >
              <template #icon>
                <icon-mdi-view-column />
              </template>
              看板
            </NButton>
            <NButton type="primary" @click="createIssue">
              <template #icon>
                <icon-mdi-plus />
              </template>
              新建 Issue
            </NButton>
          </NSpace>
        </NSpace>
      </template>

      <!-- Tabs and Filters -->
      <div class="tabs-and-filters">
        <!-- Tabs -->
        <div class="tabs-section">
          <NTabs v-model:value="activeTab" type="line" size="small" @update:value="handleTabChange">
            <NTabPane name="my_issues">
              <template #tab>
                <div class="tab-content">
                  <icon-mdi-account-check class="tab-icon" />
                  <span class="tab-label">我的待办</span>
                  <span class="tab-count" :class="{ 'tab-count-active': activeTab === 'my_issues' }">
                    {{ tabCounts.my_issues }}
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

        <!-- Search Row -->
        <div class="search-row">
          <div class="search-wrapper">
            <icon-mdi-magnify class="search-icon" />
            <IssueSmartSearch
              v-model="smartSearchValue"
              placeholder="搜索 Issue 编号、标题..."
              @search="handleSmartSearch"
            />
          </div>
          <div class="search-actions">
            <NDropdown trigger="click" :options="savedViewDropdownOptions" @select="handleSavedViewSelect">
              <NButton text size="small" class="action-btn">
                <icon-mdi-bookmark-outline />
                <span class="action-btn-text">我的视图</span>
                <icon-mdi-chevron-down class="chevron-icon" />
              </NButton>
            </NDropdown>

            <NTooltip>
              <template #trigger>
                <NButton text size="small" class="action-btn" @click="openSaveViewModal">
                  <icon-mdi-content-save-outline />
                  <span class="action-btn-text">保存视图</span>
                </NButton>
              </template>
              <div>将当前筛选保存为个人视图</div>
            </NTooltip>

            <NTooltip v-if="activeSavedViewId">
              <template #trigger>
                <NButton text size="small" class="action-btn" @click="toggleActiveViewFavorite">
                  <icon-mdi-star />
                  <span class="action-btn-text">收藏</span>
                </NButton>
              </template>
              <div>切换当前视图收藏状态</div>
            </NTooltip>

            <NTooltip>
              <template #trigger>
                <NButton text size="small" class="action-btn" @click="filtersExpanded = !filtersExpanded">
                  <icon-mdi-filter-variant />
                  <span class="action-btn-text">筛选</span>
                  <icon-mdi-chevron-down :class="{ 'icon-rotated': filtersExpanded }" class="chevron-icon" />
                </NButton>
              </template>
              <div>{{ filtersExpanded ? '收起' : '展开' }}筛选面板</div>
            </NTooltip>

            <NTooltip>
              <template #trigger>
                <NButton text size="small" class="action-btn" @click="showSyntaxHelp = !showSyntaxHelp">
                  <icon-mdi-help-circle-outline />
                  <span class="action-btn-text">语法帮助</span>
                </NButton>
              </template>
              <div>查看搜索语法帮助</div>
            </NTooltip>

            <div class="group-by-select">
              <NText depth="3" class="group-by-label">分组</NText>
              <NSelect
                :value="groupBy"
                :options="groupByOptions"
                size="small"
                style="width: 120px"
                @update:value="handleGroupByChange"
              />
            </div>
          </div>
        </div>

        <!-- Filters Row -->
        <div v-show="filtersExpanded" class="filters-row">
          <div class="filter-selectors">
            <NSelect
              v-model:value="filters.project_id"
              :options="projectOptions"
              placeholder="项目"
              clearable
              :loading="projectsLoading"
              size="small"
              @update:value="handleFilterChange"
            />
            <NSelect
              v-model:value="filters.type"
              :options="typeOptions"
              placeholder="类型"
              clearable
              size="small"
              @update:value="handleFilterChange"
            />
            <NSelect
              v-model:value="filters.priority"
              :options="priorityOptions"
              placeholder="优先级"
              clearable
              size="small"
              @update:value="handleFilterChange"
            />

            <NButton v-if="hasActiveFilters" text size="tiny" class="clear-btn" @click="clearFilters">
              <template #icon>
                <icon-mdi-close-circle />
              </template>
              重置筛选
            </NButton>
          </div>
        </div>

        <!-- 语法帮助面板 -->
        <div v-if="showSyntaxHelp" class="syntax-help-panel">
          <NCard size="small" :bordered="true" class="syntax-help-card">
            <template #header>
              <div class="syntax-help-header">
                <icon-mdi-help-circle class="syntax-icon" />
                <NText strong>搜索语法帮助</NText>
              </div>
            </template>

            <div class="syntax-examples">
              <div v-for="(example, index) in syntaxExamples" :key="index" class="syntax-example">
                <code class="syntax-code">{{ example.text }}</code>
                <NText depth="3" class="syntax-desc">{{ example.desc }}</NText>
              </div>
            </div>

            <div class="syntax-tip">
              <icon-mdi-lightbulb class="tip-icon" />
              <NText depth="3" style="font-size: 12px">
                提示：可以组合使用多个过滤器，如
                <code>is:open type:bug</code>
              </NText>
            </div>
          </NCard>
        </div>
      </div>

      <!-- Saved View favorites -->
      <div v-if="savedViews.some(v => v.isFavorite)" class="saved-view-favorites">
        <NSpace :size="6" align="center">
          <NText depth="3" style="font-size: 12px">收藏视图</NText>
          <NTag
            v-for="v in savedViews.filter(x => x.isFavorite)"
            :key="v.id"
            size="small"
            round
            :type="activeSavedViewId === v.id ? 'primary' : 'default'"
            style="cursor: pointer"
            @click="applySavedView(v)"
          >
            ★ {{ v.name }}
          </NTag>
        </NSpace>
      </div>

      <!-- Active Filters Tags -->
      <div v-if="hasActiveFilters" class="active-filters">
        <NSpace :size="6">
          <NTag
            v-if="filters.project_id"
            size="small"
            closable
            @close="
              filters.project_id = undefined;
              handleFilterChange();
            "
          >
            {{ getProjectName(filters.project_id) }}
          </NTag>
          <NTag
            v-if="filters.type"
            size="small"
            closable
            @close="
              filters.type = undefined;
              handleFilterChange();
            "
          >
            {{ getTypeLabel(filters.type) }}
          </NTag>
          <NTag
            v-if="filters.priority"
            size="small"
            closable
            @close="
              filters.priority = undefined;
              handleFilterChange();
            "
          >
            {{ getPriorityLabel(filters.priority) }}
          </NTag>
        </NSpace>
      </div>

      <NSpin :show="loading">
        <template v-if="viewMode === 'board'">
          <IssueBoard :issues="filteredIssues" @changed="loadIssues" />
        </template>
        <template v-else-if="isGroupedList">
          <IssueListGrouped :issues="filteredIssues" :group-by="activeGroupBy" :columns="columns" />
        </template>
        <template v-else>
          <NEmpty v-if="!loading && issues.length === 0" description="暂无 Issue" size="large" />
          <div v-else>
            <NDataTable
              :columns="columns"
              :data="issues"
              :row-key="(row: Api.Issue.Issue) => row.id"
              :scroll-x="1400"
              striped
              size="small"
            />
            <div class="pagination-wrapper">
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
          </div>
        </template>
      </NSpin>
    </NCard>

    <NModal
      v-model:show="saveViewModalVisible"
      preset="dialog"
      title="保存为个人视图"
      positive-text="保存"
      negative-text="取消"
      :loading="saveViewSubmitting"
      @positive-click="confirmSaveView"
    >
      <NInput v-model:value="saveViewName" placeholder="视图名称，例如：我的高优缺陷" maxlength="128" />
    </NModal>
  </div>
</template>

<style scoped>
.issue-list-container {
  padding: 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  min-height: 100vh;
}

/* Tabs and Filters 容器 */
.tabs-and-filters {
  /* border-radius: 12px; */
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  margin-bottom: 0px;
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

/* 搜索行 */
.search-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px;
  border-bottom: 1px solid var(--color-bg-tertiary);
}

/* 搜索操作按钮区域 */
.search-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  color: #606266;
  font-size: 13px;
  border-radius: 4px;
  transition: all 0.2s;
  height: 32px;
}

.action-btn:hover {
  color: #18a058;
  background: rgba(24, 160, 88, 0.08);
}

.action-btn-text {
  font-size: 12px;
}

.chevron-icon {
  transition: transform 0.3s ease;
  font-size: 14px;
}

.chevron-icon.icon-rotated {
  transform: rotate(180deg);
}

/* 语法帮助面板 */
.syntax-help-panel {
  padding: 0 16px 16px;
  border-top: 1px solid var(--color-bg-tertiary);
  background: #fafbfc;
}

.syntax-help-card {
  border-radius: 8px;
  border-color: #e8eaed;
}

.syntax-help-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.syntax-icon {
  font-size: 16px;
  color: #18a058;
}

.syntax-examples {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.syntax-example {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  gap: 12px;
}

.syntax-code {
  background: #f5f5f5;
  padding: 3px 8px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  color: #18a058;
  min-width: 120px;
}

.syntax-desc {
  font-size: 12px;
  flex: 1;
}

.syntax-tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e8eaed;
}

.tip-icon {
  font-size: 14px;
  color: #e6a23c;
  flex-shrink: 0;
  margin-top: 2px;
}

/* 筛选行过渡动画 */
.filters-row {
  transition: all 0.3s ease;
  overflow: hidden;
  padding: 12px 16px;
  background: #fafbfc;
  border-radius: 0 0 8px 8px;
}

/* 搜索区域优化 */
.search-wrapper {
  flex: 1 1 auto;
  min-width: 200px;
  max-width: 100%;
  position: relative;
  display: flex;
  align-items: center;
  background: white;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  transition: all 0.2s;
}

.search-wrapper:hover {
  border-color: #c0c4cc;
}

.search-wrapper:focus-within {
  border-color: #18a058;
  box-shadow: 0 0 0 2px rgba(24, 160, 88, 0.1);
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 16px;
  color: #c0c4cc;
  pointer-events: none;
  z-index: 2;
}

/* IssueSmartSearch 组件样式调整 */
.search-wrapper :deep(.issue-smart-search) {
  width: 100%;
}

.search-wrapper :deep(.issue-smart-search > .n-space) {
  margin: 0 !important;
}

.search-wrapper :deep(.n-auto-complete) {
  width: 100%;
}

.search-wrapper :deep(.n-input) {
  border: none !important;
  background: transparent !important;
  padding-left: 40px !important;
}

.search-wrapper :deep(.n-input__input-el) {
  font-size: 13px;
}

.search-wrapper :deep(.n-input__border),
.search-wrapper :deep(.n-input__state-border) {
  border: none !important;
  box-shadow: none !important;
}

/* 筛选器优化 - 更紧凑 */
.filter-selectors {
  display: flex;
  gap: 8px;
  align-items: center;
}

.filter-selectors .n-select {
  min-width: 120px;
  max-width: 180px;
}

.filter-selectors :deep(.n-base-selection) {
  border-radius: 4px;
  border-color: #dcdfe6;
  background: white;
  height: 28px;
}

.filter-selectors :deep(.n-base-selection .n-base-selection__border) {
  border-radius: 4px;
}

.filter-selectors :deep(.n-base-selection__action) {
  height: 26px;
}

.filter-selectors :deep(.n-base-selection__label) {
  font-size: 12px;
  height: 26px;
  line-height: 26px;
}

.filter-selectors :deep(.n-base-selection:hover) {
  border-color: #c0c4cc;
}

.filter-selectors :deep(.n-base-selection--focus) {
  border-color: #18a058;
  box-shadow: 0 0 0 2px rgba(24, 160, 88, 0.1);
}

/* 清除按钮 */
.clear-btn {
  color: #909399;
  font-size: 12px;
  border-radius: 4px;
  padding: 4px 8px;
  transition: all 0.2s;
  height: 28px;
}

.clear-btn:hover {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}

/* Active Filters */
.saved-view-favorites {
  margin: 8px 0 4px;
}

.active-filters {
  padding: 8px 16px 12px;
  background: #fafbfc;
  border-top: 1px solid var(--color-bg-tertiary);
}

/* Card 样式优化 */
.issue-list-container :deep(.n-card) {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: none;
  overflow: hidden;
}

.issue-list-container :deep(.n-card__header) {
  padding: 16px 20px;
  background: white;
  border-bottom: 1px solid #e8eaed;
}

.issue-list-container :deep(.n-card__content) {
  padding: 0;
}

/* 按钮样式优化 */
.issue-list-container :deep(.n-button--primary-type) {
  border-radius: 6px;
  font-weight: 500;
}

/* DataTable 样式优化 */
.issue-list-container :deep(.n-data-table) {
  border-radius: 0;
  border: none;
}

.issue-list-container :deep(.n-data-table-th) {
  background: #f8f9fa;
  font-weight: 600;
  color: #606266;
  border-bottom: 1px solid #e8eaed;
  padding: 12px 16px;
  font-size: 13px;
}

.issue-list-container :deep(.n-data-table-td) {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-bg-tertiary);
  font-size: 13px;
}

.issue-list-container :deep(.n-data-table-tr:hover) {
  background: #f8f9fa;
}

/* 标签样式优化 */
.issue-list-container :deep(.n-tag) {
  border-radius: 4px;
  font-weight: 500;
}

/* 空状态优化 */
.issue-list-container :deep(.n-empty) {
  padding: 60px 0;
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

/* 标题样式优化 */
.issue-list-container :deep(.n-text strong) {
  font-size: 16px;
  font-weight: 600;
}

.group-by-select {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 4px;
}

.group-by-label {
  font-size: 12px;
  white-space: nowrap;
}
</style>
