<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NCheckbox,
  NDataTable,
  NDropdown,
  NEmpty,
  NInput,
  NModal,
  NPagination,
  NPopover,
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
import { type CycleItem, fetchCycles } from '@/service/api/cycles';
import { issueApi } from '@/service/api/issue';
import {
  type SavedView,
  fetchCreateSavedView,
  fetchSaveAsSavedView,
  fetchSavedViews,
  fetchSetSavedViewFavorite,
  fetchUpdateSavedView
} from '@/service/api/saved-views';
import { fetchIssueDisplayPrefs, fetchPutIssueDisplayPrefs } from '@/service/api/display-prefs';
import { fetchAddFavorite, fetchFavorites, fetchRemoveFavorite } from '@/service/api/favorites';
import { fetchWorkspaceList } from '@/service/api/workspace';
import { useIssueStore } from '@/store/modules/issue';
import { useAuthStore } from '@/store/modules/auth';
import { useIssueFocus } from '@/composables/use-issue-focus';
import { useIssueListViewMode } from '@/composables/use-issue-list-view-mode';
import { localStg } from '@/utils/storage';
import { buildSavedViewDropdownOptions, canWriteSavedView } from '@/utils/saved-view-sections';
import { deriveListStateFromSavedView } from '@/utils/apply-saved-view';
import { GROUP_BY_OPTIONS, type GroupByKey } from '@/utils/groupIssuesBy';
import {
  type IssueDisplayFields,
  type SwimlaneBy,
  defaultIssueDisplay,
  displayStateToJson,
  normalizeIssueDisplay
} from '@/utils/display-prefs';
import { nestIssuesDepth1 } from '@/utils/nestIssuesDepth1';
import type { ParsedQuery } from '@/utils/issueSearchParser';
import IssueSmartSearch from '@/components/IssueSmartSearch.vue';
import type { Api } from '@/typings/api';
import IssueBoard from './modules/IssueBoard.vue';
import IssueListGrouped from './modules/IssueListGrouped.vue';
import DisplayOptionsPanel from './modules/DisplayOptionsPanel.vue';

defineOptions({
  name: 'IssueList'
});

const issueStore = useIssueStore();
const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

const issues = ref<Api.Issue.Issue[]>([]);
const allIssues = ref<Api.Issue.Issue[]>([]); // 保存所有 issue，用于 tab 切换
const loading = ref(false);
const projects = ref<Api.Project.Project[]>([]);
const projectsLoading = ref(false);
const cycles = ref<CycleItem[]>([]);
const cyclesLoading = ref(false);

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

// 双视图：list | board（同数据源；与 ⌘B 共享单例）
const { viewMode, setMode: setViewMode } = useIssueListViewMode();
const issueFocus = useIssueFocus();
const focusedIssueId = issueFocus.focusedIssueId;
const filteredIssues = ref<Api.Issue.Issue[]>([]);

/** E4-S2：列表分组依据（本地状态；可写入 Saved View display.group_by） */
const groupBy = ref<GroupByKey>('none');
const groupByOptions = GROUP_BY_OPTIONS;

const isGroupedList = computed(() => groupBy.value !== 'none');
const activeGroupBy = computed(() => groupBy.value as Exclude<GroupByKey, 'none'>);

/** E7-S3：会话 Display（View 覆盖会话；prefs 为个人默认） */
const displayFields = ref<IssueDisplayFields>(defaultIssueDisplay().fields);
const swimlaneBy = ref<SwimlaneBy>('none');
const hideEmptyLanes = ref(false);
const displayPrefsSaving = ref(false);
const displayPopoverShow = ref(false);

function currentDisplayJson() {
  return displayStateToJson({
    viewMode: viewMode.value,
    groupBy: groupBy.value,
    swimlaneBy: swimlaneBy.value,
    hideEmptyLanes: hideEmptyLanes.value,
    fields: displayFields.value
  });
}

function applyDisplayState(partial: {
  viewMode?: 'list' | 'board';
  groupBy?: GroupByKey;
  swimlaneBy?: SwimlaneBy;
  hideEmptyLanes?: boolean;
  fields?: IssueDisplayFields;
}) {
  if (partial.viewMode) viewMode.value = partial.viewMode;
  if (partial.groupBy) groupBy.value = partial.groupBy;
  if (partial.swimlaneBy) swimlaneBy.value = partial.swimlaneBy;
  if (typeof partial.hideEmptyLanes === 'boolean') hideEmptyLanes.value = partial.hideEmptyLanes;
  if (partial.fields) displayFields.value = { ...partial.fields };
}

async function loadPersonalDisplayPrefs() {
  try {
    const { data, error } = await fetchIssueDisplayPrefs();
    if (error || !data?.display) return;
    const normalized = normalizeIssueDisplay(data.display);
    applyDisplayState({
      viewMode: normalized.viewMode,
      groupBy: normalized.groupBy,
      swimlaneBy: normalized.swimlaneBy,
      hideEmptyLanes: normalized.hideEmptyLanes,
      fields: normalized.fields
    });
  } catch {
    /* ignore prefs load */
  }
}

async function setPersonalDisplayDefault() {
  displayPrefsSaving.value = true;
  try {
    const { error } = await fetchPutIssueDisplayPrefs(currentDisplayJson() as any);
    if (error) {
      window.$message?.error(error.message || '保存个人默认失败');
      return;
    }
    window.$message?.success('已设为个人默认显示');
  } catch {
    window.$message?.error('保存个人默认失败');
  } finally {
    displayPrefsSaving.value = false;
  }
}

function resetDisplayOptions() {
  const d = defaultIssueDisplay();
  swimlaneBy.value = d.swimlaneBy;
  hideEmptyLanes.value = d.hideEmptyLanes;
  displayFields.value = { ...d.fields };
}

/** E4-S3：当前页 depth-1 嵌套（父不在本页则子作顶层） */
type IssueRow = Api.Issue.Issue & { nestDepth?: number };
const nestedListIssues = computed<IssueRow[]>(() =>
  nestIssuesDepth1(issues.value).map(r => ({ ...r.issue, nestDepth: r.depth }))
);

// 筛选框展开状态（默认关闭）
const filtersExpanded = ref(false);

// Filters
const filters = reactive({
  status: undefined as Api.Issue.IssueStatus | undefined,
  priority: undefined as Api.Issue.IssuePriority | undefined,
  type: undefined as Api.Issue.IssueType | undefined,
  project_id: undefined as string | undefined,
  cycle_id: undefined as string | undefined,
  search: '',
  assignee_id: undefined as string | undefined,
  reporter_id: undefined as string | undefined,
  watching: undefined as boolean | undefined,
  due_soon: undefined as boolean | undefined
});

const scopeTitle = computed(() => {
  if (filters.watching) return '我关注的';
  if (filters.due_soon) return '即将到期';
  if (filters.assignee_id === 'me') return '指派给我';
  if (filters.reporter_id === 'me') return '我创建的';
  return null;
});

function clearScope() {
  applyScopeFromQuery(undefined);
  const nextQuery = { ...route.query };
  delete nextQuery.scope;
  router.replace({ query: nextQuery });
  pagination.page = 1;
  loadIssues();
}

function applyScopeFromQuery(scope: unknown) {
  filters.assignee_id = undefined;
  filters.reporter_id = undefined;
  filters.watching = undefined;
  filters.due_soon = undefined;
  if (scope === 'assigned') {
    filters.assignee_id = 'me';
    activeTab.value = 'my_issues';
  } else if (scope === 'created') {
    filters.reporter_id = 'me';
    activeTab.value = 'all';
  } else if (scope === 'watching') {
    filters.watching = true;
    activeTab.value = 'all';
  } else if (scope === 'due_soon') {
    filters.due_soon = true;
    activeTab.value = 'all';
  }
}

// 智能搜索
const smartSearchValue = ref('');

// Saved Views（E4 个人；E7-S2 共享分区）
const savedViews = ref<SavedView[]>([]);
const personalSavedViews = ref<SavedView[]>([]);
const sharedSavedViews = ref<SavedView[]>([]);
const savedViewsLoading = ref(false);
const saveViewModalVisible = ref(false);
const saveViewName = ref('');
const saveViewShared = ref(false);
const saveViewSubmitting = ref(false);
const activeSavedViewId = ref<string | null>(null);
const workspaceRole = ref<string | null>(null);

async function loadWorkspaceRole() {
  try {
    const res = await fetchWorkspaceList();
    const list = res.data || [];
    const wid = localStg.get('workspaceId');
    const current = list.find(w => w.id === wid) || list[0];
    workspaceRole.value = current?.role ?? null;
  } catch {
    workspaceRole.value = null;
  }
}

async function loadSavedViews() {
  savedViewsLoading.value = true;
  try {
    const response = await fetchSavedViews();
    const data = response.data;
    personalSavedViews.value = data?.personal || [];
    sharedSavedViews.value = data?.shared || [];
    savedViews.value = data?.rows || [...personalSavedViews.value, ...sharedSavedViews.value];
  } catch {
    personalSavedViews.value = [];
    sharedSavedViews.value = [];
    savedViews.value = [];
  } finally {
    savedViewsLoading.value = false;
  }
}

const activeSavedView = computed(() => savedViews.value.find(v => v.id === activeSavedViewId.value) || null);

const canWriteActiveSavedView = computed(() => {
  const view = activeSavedView.value;
  if (!view) return false;
  return canWriteSavedView(view, currentUserId.value, workspaceRole.value);
});

function buildCurrentFilterPayload() {
  const filter: Record<string, unknown> = {};
  if (filters.status) filter.status = filters.status;
  if (filters.type) filter.type = filters.type;
  if (filters.priority) filter.priority = filters.priority;
  if (filters.project_id) filter.project_id = filters.project_id;
  if (filters.cycle_id) filter.cycle_id = filters.cycle_id;
  if (filters.search) filter.search = filters.search;
  filter.tab = activeTab.value;
  return filter;
}

function openSaveViewModal() {
  saveViewName.value = '';
  saveViewShared.value = false;
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
      display: currentDisplayJson(),
      is_favorite: false,
      is_shared: saveViewShared.value
    });
    window.$message?.success(saveViewShared.value ? '共享视图已保存' : '视图已保存');
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
  const state = deriveListStateFromSavedView(view);
  filters.type = state.filters.type;
  filters.priority = state.filters.priority;
  filters.project_id = state.filters.project_id;
  filters.cycle_id = state.filters.cycle_id;
  filters.status = state.filters.status;
  filters.search = state.filters.search;
  smartSearchValue.value = filters.search || '';

  if (state.tab) {
    activeTab.value = state.tab;
  }

  if (state.viewMode) {
    viewMode.value = state.viewMode;
  }
  groupBy.value = state.groupBy;
  swimlaneBy.value = state.swimlaneBy;
  hideEmptyLanes.value = state.hideEmptyLanes;
  displayFields.value = { ...state.fields };

  activeSavedViewId.value = state.activeSavedViewId;
  pagination.page = 1;
  await loadIssues();
  window.$message?.success(`已应用视图「${view.name}」`);
}

async function applySavedViewById(viewId: string) {
  if (!viewId) return;
  let view = savedViews.value.find(v => v.id === viewId);
  if (!view) {
    await loadSavedViews();
    view = savedViews.value.find(v => v.id === viewId);
  }
  if (!view) {
    window.$message?.warning('未找到该视图');
    return;
  }
  await applySavedView(view);
  if (route.query.view) {
    const nextQuery = { ...route.query };
    delete nextQuery.view;
    router.replace({ path: route.path, query: nextQuery });
  }
}

async function toggleActiveViewFavorite() {
  const id = activeSavedViewId.value;
  if (!id) {
    window.$message?.info('请先应用一个已保存视图');
    return;
  }
  const view = savedViews.value.find(v => v.id === id);
  if (!view) return;
  if (view.isShared) {
    window.$message?.warning('共享视图不支持收藏，可另存为个人视图后再收藏');
    return;
  }
  try {
    await fetchSetSavedViewFavorite(view.id, !view.isFavorite);
    await loadSavedViews();
    window.$message?.success(view.isFavorite ? '已取消收藏' : '已收藏');
  } catch {
    window.$message?.error('更新收藏失败');
  }
}

const sidebarPinnedViewFavoriteId = ref<string | null>(null);
const sidebarPinLoading = ref(false);

async function loadSidebarPinForActiveView() {
  const id = activeSavedViewId.value;
  if (!id) {
    sidebarPinnedViewFavoriteId.value = null;
    return;
  }
  try {
    const res = await fetchFavorites();
    const rows = res.data?.rows || [];
    const hit = rows.find(r => r.targetType === 'saved_view' && r.targetId === id);
    sidebarPinnedViewFavoriteId.value = hit?.id ?? null;
  } catch {
    sidebarPinnedViewFavoriteId.value = null;
  }
}

watch(activeSavedViewId, () => {
  loadSidebarPinForActiveView();
});

async function toggleActiveViewSidebarPin() {
  const id = activeSavedViewId.value;
  if (!id) {
    window.$message?.info('请先应用一个已保存视图');
    return;
  }
  sidebarPinLoading.value = true;
  try {
    if (sidebarPinnedViewFavoriteId.value) {
      await fetchRemoveFavorite(sidebarPinnedViewFavoriteId.value);
      sidebarPinnedViewFavoriteId.value = null;
      window.$message?.success('已从侧栏移除');
    } else {
      const res = await fetchAddFavorite({ target_type: 'saved_view', target_id: id });
      sidebarPinnedViewFavoriteId.value = res.data?.id ?? null;
      window.$message?.success('已收藏到侧栏');
    }
    window.dispatchEvent(new CustomEvent('opentask:favorites-changed'));
  } catch {
    window.$message?.error('更新侧栏收藏失败');
  } finally {
    sidebarPinLoading.value = false;
  }
}

async function saveActiveViewAsPersonal() {
  const view = activeSavedView.value;
  if (!view) {
    window.$message?.info('请先应用一个已保存视图');
    return;
  }
  try {
    const res = await fetchSaveAsSavedView(view.id, `${view.name}（副本）`);
    window.$message?.success('已另存为个人视图');
    await loadSavedViews();
    const copy = res.data;
    if (copy?.id) {
      await applySavedView(copy);
    }
  } catch {
    window.$message?.error('另存为失败');
  }
}

const savedViewDropdownOptions = computed<DropdownOption[]>(() => {
  return buildSavedViewDropdownOptions(personalSavedViews.value, sharedSavedViews.value) as DropdownOption[];
});

const favoriteSavedViews = computed(() => personalSavedViews.value.filter(v => v.isFavorite));

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
        cycle_id: filters.cycle_id,
        search: filters.search || undefined,
        assignee_id: filters.assignee_id,
        reporter_id: filters.reporter_id,
        watching: filters.watching,
        due_soon: filters.due_soon
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
  if (filters.cycle_id) {
    if (filters.cycle_id === '__none__') {
      filtered = filtered.filter(issue => !issue.cycle_id);
    } else {
      filtered = filtered.filter(issue => issue.cycle_id === filters.cycle_id);
    }
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

async function loadCycles() {
  cyclesLoading.value = true;
  try {
    const response = await fetchCycles();
    cycles.value = response.data?.rows || [];
  } catch {
    cycles.value = [];
  } finally {
    cyclesLoading.value = false;
  }
}

const cycleFilterOptions = computed(() => {
  const opts: { label: string; value: string }[] = [{ label: '无 Cycle', value: '__none__' }];
  for (const c of cycles.value) {
    opts.push({ label: `${c.name}${c.status === 'active' ? ' (active)' : ''}`, value: c.id });
  }
  return opts;
});

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
  if (filters.cycle_id) {
    if (filters.cycle_id === '__none__') {
      base = base.filter(issue => !issue.cycle_id);
    } else {
      base = base.filter(issue => issue.cycle_id === filters.cycle_id);
    }
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

// Focus row for A/S/P/I hotkeys
function focusIssueRow(issue: Api.Issue.Issue) {
  issueFocus.setFocus(issue.id, {
    title: issue.title,
    status: issue.status,
    priority: issue.priority,
    assigneeId: issue.assignee_id
  });
}

function issueRowProps(row: Api.Issue.Issue) {
  return {
    class: issueFocus.focusedIssueId.value === row.id ? 'issue-row-focused' : undefined,
    style:
      issueFocus.focusedIssueId.value === row.id
        ? 'outline: 2px solid var(--color-primary); outline-offset: -2px;'
        : undefined,
    onClick: () => focusIssueRow(row)
  };
}

// View issue detail
function viewIssue(issue: Api.Issue.Issue) {
  focusIssueRow(issue);
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
  if (!id || !canWriteActiveSavedView.value) return;
  try {
    await fetchUpdateSavedView(id, {
      display: currentDisplayJson()
    });
    await loadSavedViews();
  } catch {
    window.$message?.warning('分组已切换，但同步到已保存视图失败');
  }
}

async function syncActiveViewDisplay() {
  const id = activeSavedViewId.value;
  if (!id || !canWriteActiveSavedView.value) return;
  try {
    await fetchUpdateSavedView(id, { display: currentDisplayJson() });
    await loadSavedViews();
  } catch {
    /* non-blocking */
  }
}

function onDisplayFieldsUpdate(next: IssueDisplayFields) {
  displayFields.value = next;
  syncActiveViewDisplay();
}

function onSwimlaneByUpdate(next: SwimlaneBy) {
  swimlaneBy.value = next;
  syncActiveViewDisplay();
}

function onHideEmptyLanesUpdate(next: boolean) {
  hideEmptyLanes.value = next;
  syncActiveViewDisplay();
}

// Clear all filters
function clearFilters() {
  filters.project_id = undefined;
  filters.cycle_id = undefined;
  filters.type = undefined;
  filters.status = undefined;
  filters.priority = undefined;
  filters.search = '';
  smartSearchValue.value = '';
  applyTabAndFilters();
}

// Computed: Check if any filters are active
const hasActiveFilters = computed(() => {
  return Boolean(
    filters.project_id || filters.cycle_id || filters.type || filters.status || filters.priority || filters.search
  );
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
    ellipsis: { tooltip: true },
    render: (row: Api.Issue.Issue & { nestDepth?: number }) => {
      const depth = row.nestDepth || 0;
      return h(
        'span',
        {
          style: {
            display: 'inline-block',
            paddingLeft: `${depth * 16}px`,
            maxWidth: '100%'
          }
        },
        [
          depth > 0
            ? h(
                'span',
                {
                  style: {
                    opacity: 0.55,
                    marginRight: '4px',
                    color: 'var(--color-text-tertiary, #9ca3af)'
                  }
                },
                '↳'
              )
            : null,
          row.title
        ]
      );
    }
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
    title: '估点',
    key: 'estimate_points',
    width: 72,
    render: row => (row.estimate_points != null ? String(row.estimate_points) : '—')
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

watch(
  () => route.query.view,
  viewId => {
    if (typeof viewId === 'string' && viewId) {
      applySavedViewById(viewId).catch(() => undefined);
    }
  }
);

watch(
  () => route.query.cycle_id,
  cycleId => {
    const next = typeof cycleId === 'string' && cycleId ? cycleId : undefined;
    if (filters.cycle_id !== next) {
      filters.cycle_id = next;
      pagination.page = 1;
      loadIssues();
    }
  }
);

watch(
  () => route.query.scope,
  scope => {
    applyScopeFromQuery(scope);
    pagination.page = 1;
    loadIssues();
  }
);

onMounted(async () => {
  loadProjects();
  loadCycles();
  await loadWorkspaceRole();
  await loadSavedViews();
  const viewId = route.query.view;
  const cycleQ = route.query.cycle_id;
  if (typeof cycleQ === 'string' && cycleQ) {
    filters.cycle_id = cycleQ;
  }
  applyScopeFromQuery(route.query.scope);
  if (typeof viewId === 'string' && viewId) {
    await applySavedViewById(viewId);
  } else {
    await loadPersonalDisplayPrefs();
    await loadIssues();
  }
});
</script>

<template>
  <div class="issue-list-container">
    <NCard :bordered="false">
      <NAlert v-if="scopeTitle" type="info" :bordered="false" class="mb-12px" closable @close="clearScope">
        当前视图：{{ scopeTitle }}
      </NAlert>
      <template #header>
        <NSpace align="center" justify="space-between" style="width: 100%">
          <NText strong style="font-size: 16px">Issue 管理</NText>
          <NSpace align="center">
            <NButton
              size="small"
              :type="viewMode === 'list' ? 'primary' : 'default'"
              secondary
              @click="setViewMode('list')"
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
              @click="setViewMode('board')"
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
                <span class="action-btn-text">视图</span>
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
              <div>将当前筛选保存为个人或共享视图</div>
            </NTooltip>

            <NTooltip v-if="activeSavedViewId && activeSavedView && !activeSavedView.isShared">
              <template #trigger>
                <NButton text size="small" class="action-btn" @click="toggleActiveViewFavorite">
                  <icon-mdi-star />
                  <span class="action-btn-text">星标</span>
                </NButton>
              </template>
              <div>星标视图（列表顶栏 chips，≠ 侧栏收藏）</div>
            </NTooltip>

            <NTooltip v-if="activeSavedViewId">
              <template #trigger>
                <NButton
                  text
                  size="small"
                  class="action-btn"
                  :loading="sidebarPinLoading"
                  @click="toggleActiveViewSidebarPin"
                >
                  <icon-mdi-pin-outline />
                  <span class="action-btn-text">{{ sidebarPinnedViewFavoriteId ? '取消侧栏' : '收藏到侧栏' }}</span>
                </NButton>
              </template>
              <div>固定到左侧边栏 Favorites（独立于星标）</div>
            </NTooltip>

            <NTooltip v-if="activeSavedViewId">
              <template #trigger>
                <NButton text size="small" class="action-btn" @click="saveActiveViewAsPersonal">
                  <icon-mdi-content-copy />
                  <span class="action-btn-text">另存为</span>
                </NButton>
              </template>
              <div>复制为个人视图（共享只读成员可用）</div>
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

            <NPopover v-model:show="displayPopoverShow" trigger="click" placement="bottom-end">
              <template #trigger>
                <NButton text size="small" class="action-btn">
                  <icon-mdi-eye-outline />
                  <span class="action-btn-text">显示</span>
                </NButton>
              </template>
              <DisplayOptionsPanel
                :fields="displayFields"
                :swimlane-by="swimlaneBy"
                :hide-empty-lanes="hideEmptyLanes"
                :saving="displayPrefsSaving"
                @update:fields="onDisplayFieldsUpdate"
                @update:swimlane-by="onSwimlaneByUpdate"
                @update:hide-empty-lanes="onHideEmptyLanesUpdate"
                @set-personal-default="setPersonalDisplayDefault"
                @reset="resetDisplayOptions"
              />
            </NPopover>

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
              v-model:value="filters.cycle_id"
              :options="cycleFilterOptions"
              placeholder="Cycle"
              clearable
              :loading="cyclesLoading"
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
      <div v-if="favoriteSavedViews.length" class="saved-view-favorites">
        <NSpace :size="6" align="center">
          <NText depth="3" style="font-size: 12px">收藏视图</NText>
          <NTag
            v-for="v in favoriteSavedViews"
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
          <IssueBoard
            :issues="filteredIssues"
            :swimlane-by="swimlaneBy"
            :hide-empty-lanes="hideEmptyLanes"
            :fields="displayFields"
            @changed="loadIssues"
          />
        </template>
        <template v-else-if="isGroupedList">
          <IssueListGrouped
            :issues="filteredIssues"
            :group-by="activeGroupBy"
            :columns="columns"
            :row-props="issueRowProps"
          />
        </template>
        <template v-else>
          <NEmpty v-if="!loading && issues.length === 0" description="暂无 Issue" size="large" />
          <div v-else>
            <NDataTable
              :columns="columns"
              :data="nestedListIssues"
              :row-key="(row: Api.Issue.Issue) => row.id"
              :row-props="issueRowProps"
              :row-class-name="(row: Api.Issue.Issue) => (focusedIssueId === row.id ? 'issue-row-focused' : '')"
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
      :title="saveViewShared ? '保存为共享视图' : '保存为个人视图'"
      positive-text="保存"
      negative-text="取消"
      :loading="saveViewSubmitting"
      @positive-click="confirmSaveView"
    >
      <NSpace vertical :size="12">
        <NInput v-model:value="saveViewName" placeholder="视图名称，例如：我的高优缺陷" maxlength="128" />
        <NCheckbox v-model:checked="saveViewShared">共享给工作区</NCheckbox>
      </NSpace>
    </NModal>
  </div>
</template>

<style scoped>
.issue-list-container {
  padding: 12px;
  background: var(--color-canvas);
  min-height: 100vh;
}

/* Tabs and Filters 容器 */
.tabs-and-filters {
  /* border-radius: 12px; */
  background: var(--color-bg-primary);
  box-shadow: none;
  overflow: hidden;
  margin-bottom: 0px;
}

/* Tabs 区域 */
.tabs-section {
  padding: 0 16px;
  border-bottom: 1px solid var(--color-hairline);
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
  color: var(--color-text-tertiary);
  background: var(--color-bg-tertiary);
  border-radius: 9px;
  transition: all 0.2s;
}

.tab-count-active {
  color: white;
  background: var(--color-primary);
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
  color: var(--color-text-secondary);
  font-size: 13px;
  border-radius: 4px;
  transition: all 0.2s;
  height: 32px;
}

.action-btn:hover {
  color: var(--color-primary);
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
  background: var(--color-bg-secondary);
}

.syntax-help-card {
  border-radius: 8px;
  border-color: var(--color-hairline);
}

.syntax-help-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.syntax-icon {
  font-size: 16px;
  color: var(--color-primary);
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
  background: var(--color-bg-tertiary);
  padding: 3px 8px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  color: var(--color-primary);
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
  border-top: 1px solid var(--color-hairline);
}

.tip-icon {
  font-size: 14px;
  color: var(--color-warning);
  flex-shrink: 0;
  margin-top: 2px;
}

/* 筛选行过渡动画 */
.filters-row {
  transition: all 0.3s ease;
  overflow: hidden;
  padding: 12px 16px;
  background: var(--color-bg-secondary);
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
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-default);
  border-radius: 6px;
  transition: all 0.2s;
}

.search-wrapper:hover {
  border-color: var(--color-border-strong);
}

.search-wrapper:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 18%, transparent);
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 16px;
  color: var(--color-text-tertiary);
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
  border-color: var(--color-border-default);
  background: var(--color-bg-primary);
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
  border-color: var(--color-border-strong);
}

.filter-selectors :deep(.n-base-selection--focus) {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 18%, transparent);
}

/* 清除按钮 */
.clear-btn {
  color: var(--color-text-tertiary);
  font-size: 12px;
  border-radius: 4px;
  padding: 4px 8px;
  transition: all 0.2s;
  height: 28px;
}

.clear-btn:hover {
  color: var(--color-danger);
  background: rgba(245, 108, 108, 0.1);
}

/* Active Filters */
.saved-view-favorites {
  margin: 8px 0 4px;
}

.active-filters {
  padding: 8px 16px 12px;
  background: var(--color-bg-secondary);
  border-top: 1px solid var(--color-bg-tertiary);
}

/* Card 样式优化 */
.issue-list-container :deep(.n-card) {
  border-radius: 12px;
  box-shadow: none;
  border: none;
  overflow: hidden;
}

.issue-list-container :deep(.n-card__header) {
  padding: 16px 20px;
  background: var(--color-bg-primary);
  border-bottom: 1px solid var(--color-hairline);
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
  background: var(--color-bg-secondary);
  font-weight: 600;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-hairline);
  padding: 12px 16px;
  font-size: 13px;
}

.issue-list-container :deep(.n-data-table-td) {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-bg-tertiary);
  font-size: 13px;
}

.issue-list-container :deep(.n-data-table-tr:hover) {
  background: var(--color-bg-secondary);
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
  background: var(--color-bg-primary);
  border-top: 1px solid var(--color-hairline);
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
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

.pagination-wrapper :deep(.n-pagination-item:hover:not(.n-pagination-item--disabled)) {
  border-color: var(--color-primary);
  color: var(--color-primary);
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

:deep(.issue-row-focused td) {
  background: color-mix(in srgb, var(--color-primary) 8%, transparent);
}
</style>
