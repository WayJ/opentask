<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NAlert,
  NButton,
  NCard,
  NDatePicker,
  NEmpty,
  NInput,
  NModal,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  NText
} from 'naive-ui';
import {
  getIssuePriorityTagType,
  getIssueStatusTagType,
  getIssueTypeTagType,
  issuePriorityOptions,
  issueStatusOptions,
  issueTypeOptions
} from '@/constants/issue';
import { fetchProjectMilestones, projectApi } from '@/service/api/project';
import { type CycleItem, fetchCycles } from '@/service/api/cycles';
import { type TagItem, tagApi } from '@/service/api/tag';
import { issueApi } from '@/service/api/issue';
import { useIssueStore } from '@/store/modules/issue';
import { useAuthStore } from '@/store/modules/auth';
import { useIssueFocus } from '@/composables/use-issue-focus';
import MarkdownEditor from '@/components/MarkdownEditor.vue';
import MarkdownRenderer from '@/components/MarkdownRenderer.vue';
import IssueReactions from '@/components/IssueReactions.vue';
import UserSelect from '@/components/UserSelect.vue';
import AttachmentList from '@/components/common/AttachmentList.vue';
import EditableField from '@/components/EditableField.vue';
import type { Api } from '@/typings/api';

defineOptions({
  name: 'IssueDetail'
});

const route = useRoute();
const router = useRouter();
const issueStore = useIssueStore();
const authStore = useAuthStore();
const issueFocus = useIssueFocus();

const issueId = computed(() => (route.query.id as string) || '');
// 获取当前登录用户 ID
const currentUserId = computed(() => authStore.userInfo.userId || 'admin');
const issue = ref<Api.Issue.Issue | null>(null);
const loading = ref(false);

// Comments
const comments = ref<Api.Issue.IssueComment[]>([]);
const commentsLoading = ref(false);
const newComment = ref('');

// Timeline
const timeline = ref<Api.Issue.IssueTimeline[]>([]);
const timelineLoading = ref(false);

// Attachments
const attachments = ref<Api.Document.Response[]>([]);
const attachmentsLoading = ref(false);

// 快速操作
const showAgentPromptModal = ref(false);

// 过滤掉 commented 类型的 timeline 记录（因为评论已经在 comments 数组中完整显示）
const nonCommentTimeline = computed(() => {
  return timeline.value.filter(item => item.action_type !== 'commented');
});

// Relations
const relations = ref<{
  as_source: Api.Issue.IssueRelation[];
  as_target: Api.Issue.IssueRelation[];
} | null>(null);

// E4-S3 父子
const parentIssue = ref<Api.Issue.Issue | null>(null);
const childSummaries = ref<Api.Issue.IssueChildSummary[]>([]);
const showAddSubIssue = ref(false);
const newSubIssueTitle = ref('');
const addingSubIssue = ref(false);

// Tags
const tags = ref<Api.Issue.IssueTag[]>([]);
const availableTags = ref<TagItem[]>([]);
const showAddTag = ref(false);
const pendingTagId = ref<number | null>(null);

// Reactions
const reactions = ref<Record<string, string[]>>({});

// Projects list for select
const projects = ref<Api.Project.Project[]>([]);
const cycles = ref<CycleItem[]>([]);
const milestones = ref<Api.Project.Milestone[]>([]);

// User map for timeline display (reserved for future use)
// const userMap = ref<Map<string, { sso_name?: string; sso_account?: string; id: string }>>(new Map());

// Project options for select (with safety check)
const projectOptions = computed(() => {
  if (!Array.isArray(projects.value)) {
    console.warn('projects.value is not an array:', projects.value);
    return [];
  }
  const options = projects.value.map(p => ({
    label: p.name || p.id || 'Unnamed Project',
    value: p.id
  }));
  console.log('Project options:', options);
  return options;
});

const cycleOptions = computed(() => {
  const opts: { label: string; value: string | null }[] = [{ label: '无 Cycle', value: null }];
  for (const c of cycles.value) {
    opts.push({ label: c.name, value: c.id });
  }
  return opts;
});

const cycleDisplayValue = computed(() => {
  if (!issue.value?.cycle_id) return '未分配';
  const found = cycles.value.find(c => c.id === issue.value?.cycle_id);
  return found?.name || issue.value.cycle_id;
});

const milestoneOptions = computed(() => {
  const opts: { label: string; value: string | null }[] = [{ label: '无 Milestone', value: null }];
  for (const m of milestones.value) {
    opts.push({ label: m.name, value: m.id });
  }
  return opts;
});

const milestoneDisplayValue = computed(() => {
  if (!issue.value?.milestone_id) return '未分配';
  const found = milestones.value.find(m => m.id === issue.value?.milestone_id);
  return found?.name || issue.value.milestone_id;
});

// Editing states - 为每个字段创建独立状态
const editingStatus = ref(false);
const editingPriority = ref(false);
const editingType = ref(false);
const editingAssignee = ref(false);
const editingReporter = ref(false);
const editingDueDate = ref(false);
const editingProject = ref(false);
const editingCycle = ref(false);
const editingMilestone = ref(false);

// 临时值
const tempStatus = ref<string | null>(null);
const tempPriority = ref<string | null>(null);
const tempType = ref<string | null>(null);
const tempAssignee = ref<string | null>(null);
const tempReporter = ref<string | null>(null);
const tempDueDate = ref<number | null>(null);
const tempProject = ref<string | null>(null);
const tempCycle = ref<string | null>(null);
const tempMilestone = ref<string | null>(null);

// Constants for template
const getTypeType = getIssueTypeTagType;
const getStatusType = getIssueStatusTagType;
const getPriorityType = getIssuePriorityTagType;
const statusOptions = issueStatusOptions;
const priorityOptions = issuePriorityOptions;
const typeOptions = issueTypeOptions;

// Load issue detail
async function loadIssue() {
  if (!issueId.value) return;

  loading.value = true;
  try {
    const data = await issueStore.getIssue(issueId.value);
    issue.value = data;
    // 加载相关数据
    Promise.all([
      loadComments(),
      loadTimeline(),
      loadRelations(),
      loadTags(),
      loadAvailableTags(),
      loadReactions(),
      loadAttachments(),
      loadParentAndChildren()
    ]);
  } finally {
    loading.value = false;
  }
}

// Load comments
async function loadComments() {
  if (!issueId.value) return;

  commentsLoading.value = true;
  try {
    const data = await issueStore.getComments(issueId.value);
    comments.value = data.rows || [];
  } finally {
    commentsLoading.value = false;
  }
}

// Load timeline
async function loadTimeline() {
  if (!issueId.value) return;

  timelineLoading.value = true;
  try {
    const data = await issueStore.getTimeline(issueId.value);
    timeline.value = data || [];
  } finally {
    timelineLoading.value = false;
  }
}

// Load attachments
async function loadAttachments() {
  if (!issueId.value) return;

  attachmentsLoading.value = true;
  try {
    const response = await issueApi.getAttachments(issueId.value);
    // API 返回 {data: Array, error: null, response: {...}}
    const attachmentsData = response?.data || response || [];
    attachments.value = Array.isArray(attachmentsData) ? attachmentsData : [];
  } catch (error) {
    console.error('加载附件失败:', error);
    attachments.value = [];
  } finally {
    attachmentsLoading.value = false;
  }
}

// 快速操作：刷新数据
async function refreshData() {
  await loadIssue();
  window.$message?.success('数据已刷新');
}

// 快速操作：获取 Agent 指令
function showAgentPrompt() {
  showAgentPromptModal.value = true;
}

// 生成单个问题的 Agent 指令
function generateIssueAgentPrompt() {
  if (!issue.value) return '';

  const issueData = issue.value;

  // 获取状态文本
  const statusTextMap: Record<string, string> = {
    open: '待处理',
    in_progress: '进行中',
    feedback: '等待反馈',
    resolved: '已解决',
    closed: '已关闭',
    rejected: '已拒绝'
  };
  const statusText = statusTextMap[issueData.status] || issueData.status;

  // 获取优先级文本
  const priorityTextMap: Record<string, string> = {
    urgent: '紧急',
    high: '高',
    medium: '中',
    low: '低'
  };
  const priorityText = priorityTextMap[issueData.priority] || issueData.priority;

  // 获取类型文本
  const typeTextMap: Record<string, string> = {
    bug: 'Bug',
    feature: '功能',
    improvement: '改进',
    task: '任务'
  };
  const typeText = typeTextMap[issueData.type] || issueData.type;

  // 获取负责人信息
  const assigneeInfo = issueData.assignee
    ? issueData.assignee.sso_name || issueData.assignee.sso_account || issueData.assignee.id
    : '未分配';

  // 生成下一步操作建议
  let nextSteps = '';

  if (issueData.status === 'open') {
    nextSteps = `## 下一步工作

**当前状态：待处理**

建议操作：

1. **开始处理此问题**
\`\`\`bash
opentask-cli issue update ${issueData.issue_code} --status in_progress
\`\`\`

2. **添加评论说明处理计划**
\`\`\`bash
opentask-cli issue comment ${issueData.issue_code} "开始分析这个问题，计划..."
\`\`\`

---

**查看问题详情：**
\`\`\`bash
opentask-cli issue view ${issueData.issue_code}
\`\`\``;
  } else if (issueData.status === 'in_progress') {
    nextSteps = `## 下一步工作

**当前状态：进行中**

建议操作：

1. **更新处理进展**
\`\`\`bash
opentask-cli issue comment ${issueData.issue_code} "已完成以下工作：..."
\`\`\`

2. **标记为已解决**
\`\`\`bash
opentask-cli issue update ${issueData.issue_code} --status resolved
\`\`\`

---

**查看问题详情：**
\`\`\`bash
opentask-cli issue view ${issueData.issue_code}
\`\`\``;
  } else if (issueData.status === 'resolved') {
    nextSteps = `## 下一步工作

**当前状态：已解决**

建议操作：

1. **验证通过，关闭问题**
\`\`\`bash
opentask-cli issue update ${issueData.issue_code} --status closed
\`\`\`

2. **有问题重新打开**
\`\`\`bash
opentask-cli issue update ${issueData.issue_code} --status open
\`\`\`

---

**查看问题详情：**
\`\`\`bash
opentask-cli issue view ${issueData.issue_code}
\`\`\``;
  } else if (issueData.status === 'feedback') {
    nextSteps = `## 下一步工作

**当前状态：等待反馈**

建议操作：

1. **提供反馈信息**
\`\`\`bash
opentask-cli issue comment ${issueData.issue_code} "以下是需要反馈的内容：..."
\`\`\`

2. **反馈完成后继续处理**
\`\`\`bash
opentask-cli issue update ${issueData.issue_code} --status in_progress
\`\`\`

---

**查看问题详情：**
\`\`\`bash
opentask-cli issue view ${issueData.issue_code}
\`\`\``;
  } else {
    nextSteps = `## 下一步工作

**当前状态：${statusText}**

**常用操作：**

查看问题详情：
\`\`\`bash
opentask-cli issue view ${issueData.issue_code}
\`\`\`

更新问题状态：
\`\`\`bash
opentask-cli issue update ${issueData.issue_code} --status <new-status>
\`\`\`

添加评论：
\`\`\`bash
opentask-cli issue comment ${issueData.issue_code} "评论内容"
\`\`\``;
  }

  const description = issueData.description && issueData.description.trim() ? issueData.description : '暂无描述';

  return `# Issue: ${issueData.title}

ID: ${issueData.issue_code}
类型: ${typeText}
状态: ${statusText}
优先级: ${priorityText}
负责人: ${assigneeInfo}

## 问题描述

${description}

${nextSteps}`;
}

// 复制问题 Agent 指令
async function copyIssuePrompt() {
  const prompt = generateIssueAgentPrompt();
  if (!prompt) {
    window.$message?.error('无法生成指令');
    return;
  }

  try {
    await navigator.clipboard.writeText(prompt);
    window.$message?.success('指令已复制到剪贴板');
  } catch {
    window.$message?.error('复制失败，请手动复制');
  }
}

async function loadParentAndChildren() {
  parentIssue.value = null;
  childSummaries.value = [];
  if (!issue.value) return;

  childSummaries.value = issue.value.children || [];
  try {
    const fromApi = await issueApi.getChildren(issue.value.id);
    if (fromApi?.rows) childSummaries.value = fromApi.rows;
  } catch {
    // keep children from detail payload
  }

  if (issue.value.parent_issue_id) {
    try {
      parentIssue.value = await issueApi.getIssue(issue.value.parent_issue_id);
    } catch {
      parentIssue.value = null;
    }
  }
}

async function createSubIssue() {
  if (!issue.value || !newSubIssueTitle.value.trim()) {
    window.$message?.warning('请输入子 Issue 标题');
    return;
  }
  addingSubIssue.value = true;
  try {
    const created = await issueApi.createIssue({
      title: newSubIssueTitle.value.trim(),
      type: issue.value.type || 'feature',
      status: 'open',
      priority: issue.value.priority || 'medium',
      reporter_id: currentUserId.value,
      parent_issue_id: issue.value.id,
      project_id: issue.value.project_id
    } as Api.Issue.CreateIssue);
    window.$message?.success('子 Issue 已创建');
    showAddSubIssue.value = false;
    newSubIssueTitle.value = '';
    await loadIssue();
    if (created?.id) {
      router.push({ path: '/issue/detail', query: { id: created.id } });
    }
  } catch (e: any) {
    window.$message?.error(e?.message || '创建子 Issue 失败');
  } finally {
    addingSubIssue.value = false;
  }
}

// Load relations
async function loadRelations() {
  if (!issueId.value) return;

  try {
    const data = await issueStore.getRelations(issueId.value);
    relations.value = data;
  } catch {
    // Silently fail
  }
}

// Load tags
async function loadTags() {
  if (!issueId.value) return;

  try {
    const data = await issueStore.getTags(issueId.value);
    tags.value = data || [];
  } catch {
    // Silently fail
  }
}

function tagDisplayName(tag: Api.Issue.IssueTag) {
  return tag.name || tag.tag?.name || String(tag.id ?? tag.tag_id ?? '');
}

function tagDisplayColor(tag: Api.Issue.IssueTag) {
  return tag.color || tag.tag?.color || '#3b82f6';
}

function tagNumericId(tag: Api.Issue.IssueTag) {
  return Number(tag.id ?? tag.tag_id);
}

async function loadAvailableTags() {
  try {
    const res = await tagApi.list();
    availableTags.value = res.data?.rows || [];
  } catch {
    availableTags.value = [];
  }
}

async function handleAddTag() {
  if (!issueId.value || pendingTagId.value === null) return;
  try {
    await issueStore.addTag(issueId.value, pendingTagId.value);
    pendingTagId.value = null;
    showAddTag.value = false;
    await loadTags();
    window.$message?.success?.('标签已添加');
  } catch (e: any) {
    window.$message?.error?.(e?.message || '添加标签失败');
  }
}

async function handleRemoveTag(tag: Api.Issue.IssueTag) {
  if (!issueId.value) return;
  const id = tagNumericId(tag);
  if (Number.isNaN(id)) return;
  try {
    await issueStore.removeTag(issueId.value, id);
    await loadTags();
    window.$message?.success?.('标签已移除');
  } catch (e: any) {
    window.$message?.error?.(e?.message || '移除标签失败');
  }
}

// Load reactions
async function loadReactions() {
  if (!issueId.value) return;

  try {
    reactions.value = await issueStore.getReactions(issueId.value);
  } catch {
    reactions.value = {};
  }
}

// Load projects
async function loadCycles() {
  try {
    const response = await fetchCycles();
    cycles.value = response.data?.rows || [];
  } catch {
    cycles.value = [];
  }
}

async function loadMilestones(projectId?: string | null) {
  const pid = projectId || issue.value?.project_id;
  if (!pid) {
    milestones.value = [];
    return;
  }
  try {
    const response = await fetchProjectMilestones(pid);
    milestones.value = response.data || [];
  } catch {
    milestones.value = [];
  }
}

async function loadProjects() {
  try {
    const response = await projectApi.getList();
    // 响应拦截器已提取 data 字段，直接返回数组
    // 但需要确保 response 是数组
    console.log('Projects API raw response:', response);
    console.log('Response type:', typeof response);
    console.log('Is array?', Array.isArray(response));

    if (Array.isArray(response)) {
      projects.value = response;
      console.log('Loaded projects:', projects.value);
      console.log('First project structure:', projects.value[0]);
    } else {
      console.warn('Projects API response is not an array:', response);
      // 尝试从可能的包装对象中提取数据
      if (response && typeof response === 'object') {
        if (Array.isArray((response as any).data)) {
          projects.value = (response as any).data;
        } else if (Array.isArray((response as any).rows)) {
          projects.value = (response as any).rows;
        } else {
          projects.value = [];
        }
      } else {
        projects.value = [];
      }
    }
  } catch (error) {
    console.error('Failed to load projects:', error);
    projects.value = [];
  }
}

// Handle reaction
async function handleReact(emoji: string) {
  if (!issueId.value) return;

  try {
    await issueStore.addReaction(issueId.value, emoji);

    // 更新本地状态
    const currentUsers = reactions.value[emoji] || [];
    if (!currentUsers.includes(currentUserId.value)) {
      reactions.value = {
        ...reactions.value,
        [emoji]: [...currentUsers, currentUserId.value]
      };
    }

    window.$message?.success('反应已添加');
  } catch {
    window.$message?.error('添加反应失败');
  }
}

// Handle unreact
async function handleUnreact(emoji: string) {
  if (!issueId.value) return;

  try {
    await issueStore.removeReaction(issueId.value, emoji);

    // 更新本地状态
    const currentUsers = reactions.value[emoji] || [];
    reactions.value = {
      ...reactions.value,
      [emoji]: currentUsers.filter(u => u !== currentUserId.value)
    };

    window.$message?.success('反应已移除');
  } catch {
    window.$message?.error('移除反应失败');
  }
}

// Inline editing functions
async function saveStatus() {
  if (!issueId.value || tempStatus.value === null) return;
  try {
    await issueStore.updateStatus(issueId.value, tempStatus.value);
    await loadIssue();
    window.$message?.success('状态更新成功');
  } catch {
    window.$message?.error('状态更新失败');
  }
}

function cancelStatus() {
  tempStatus.value = null;
  editingStatus.value = false;
}

async function savePriority() {
  if (!issueId.value || tempPriority.value === null) return;
  try {
    await issueStore.updatePriority(issueId.value, tempPriority.value);
    await loadIssue();
    window.$message?.success('优先级更新成功');
  } catch {
    window.$message?.error('优先级更新失败');
  }
}

function cancelPriority() {
  tempPriority.value = null;
  editingPriority.value = false;
}

async function saveType() {
  if (!issueId.value || tempType.value === null) return;
  try {
    await issueStore.updateIssue(issueId.value, { type: tempType.value });
    await loadIssue();
    window.$message?.success('类型更新成功');
  } catch {
    window.$message?.error('类型更新失败');
  }
}

function cancelType() {
  tempType.value = null;
  editingType.value = false;
}

async function saveAssignee() {
  if (!issueId.value) return;
  try {
    await issueStore.updateAssignee(issueId.value, tempAssignee.value || undefined);
    await loadIssue();
    window.$message?.success('负责人更新成功');
  } catch {
    window.$message?.error('负责人更新失败');
  }
}

function cancelAssignee() {
  tempAssignee.value = null;
  editingAssignee.value = false;
}

async function saveReporter() {
  if (!issueId.value) return;
  try {
    await issueStore.updateReporter(issueId.value, tempReporter.value || undefined);
    await loadIssue();
    window.$message?.success('报告人更新成功');
  } catch {
    window.$message?.error('报告人更新失败');
  }
}

function cancelReporter() {
  tempReporter.value = null;
  editingReporter.value = false;
}

async function saveDueDate() {
  if (!issueId.value) return;
  try {
    await issueStore.updateIssue(issueId.value, { due_date: tempDueDate.value });
    await loadIssue();
    window.$message?.success('截止日期更新成功');
  } catch {
    window.$message?.error('截止日期更新失败');
  }
}

function cancelDueDate() {
  tempDueDate.value = null;
  editingDueDate.value = false;
}

async function saveProject() {
  if (!issueId.value) return;
  try {
    await issueStore.updateIssue(issueId.value, { project_id: tempProject.value || undefined });
    await loadIssue();
    window.$message?.success('项目更新成功');
  } catch {
    window.$message?.error('项目更新失败');
  }
}

function cancelProject() {
  tempProject.value = null;
  editingProject.value = false;
}

async function saveCycle() {
  if (!issueId.value) return;
  try {
    await issueStore.updateIssue(issueId.value, { cycle_id: tempCycle.value || null });
    await loadIssue();
    window.$message?.success('Cycle 更新成功');
  } catch {
    window.$message?.error('Cycle 更新失败');
  }
}

function cancelCycle() {
  tempCycle.value = null;
  editingCycle.value = false;
}

async function saveMilestone() {
  if (!issueId.value) return;
  try {
    await issueStore.updateIssue(issueId.value, { milestone_id: tempMilestone.value || null });
    await loadIssue();
    window.$message?.success('Milestone 更新成功');
  } catch {
    window.$message?.error('Milestone 更新失败');
  }
}

function cancelMilestone() {
  tempMilestone.value = null;
  editingMilestone.value = false;
}

// Add comment
async function handleAddComment() {
  if (!newComment.value.trim() || !issueId.value) return;

  try {
    await issueStore.addComment(issueId.value, newComment.value);
    newComment.value = '';
    await loadComments();
    await loadTimeline();
    window.$message?.success('评论添加成功');
  } catch {
    window.$message?.error('评论添加失败');
  }
}

// Delete comment
async function handleDeleteComment(commentId: string) {
  window.$dialog?.warning({
    title: '确认删除',
    content: '确定要删除这条评论吗？',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await issueStore.deleteComment(commentId);
        await loadComments();
        window.$message?.success('评论删除成功');
      } catch {
        window.$message?.error('评论删除失败');
      }
    }
  });
}

// Delete issue
function handleDeleteIssue() {
  if (!issue.value) return;

  window.$dialog?.warning({
    title: '确认删除',
    content: `确定要删除 Issue "${issue.value.title}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await issueStore.deleteIssue(issue.value!.id);
        router.push('/issue/list');
        window.$message?.success('Issue 删除成功');
      } catch {
        window.$message?.error('Issue 删除失败');
      }
    }
  });
}

// Format date
function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString();
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

// Format timeline action text
// 辅助函数：获取状态的中文标签
function getStatusLabel(status: string) {
  return statusOptions.find(s => s.value === status)?.label || status;
}

// 辅助函数：获取优先级的中文标签
function getPriorityLabel(priority: string) {
  return priorityOptions.find(p => p.value === priority)?.label || priority;
}

// 辅助函数：格式化用户信息
function formatUserInfo(user: any) {
  if (!user) return '未分配';
  // 如果是对象（新格式）
  if (typeof user === 'object') {
    return user.sso_name || user.name || user.sso_account || user.id || '未分配';
  }
  // 如果是字符串（旧格式，用户ID）
  return user;
}

// 辅助函数：格式化状态变更
function formatStatusChange(actionData: any): string {
  return `将状态从 "${getStatusLabel(actionData?.from || '')}" 改为 "${getStatusLabel(actionData?.to || '')}"`;
}

// 辅助函数：格式化负责人变更
function formatAssignedChange(actionData: any): string {
  return `将负责人从 "${formatUserInfo(actionData?.from)}" 改为 "${formatUserInfo(actionData?.to)}"`;
}

// 辅助函数：格式化优先级变更
function formatPriorityChange(actionData: any): string {
  return `将优先级从 "${getPriorityLabel(actionData?.from || '')}" 改为 "${getPriorityLabel(actionData?.to || '')}"`;
}

// 辅助函数：格式化反应动作
function formatReactionAction(actionData: any, actionType: string): string {
  const emoji = actionData?.emoji || '';
  return actionType === 'reaction_added' ? `添加了反应 ${emoji}` : `移除了反应 ${emoji}`;
}

function formatTimelineAction(item: Api.Issue.IssueTimeline): string {
  const { action_type, action_data } = item;

  switch (action_type) {
    case 'created':
      return '创建了此 Issue';
    case 'updated':
      return '更新了 Issue';
    case 'commented':
      return '添加了评论';
    case 'status_changed':
      return formatStatusChange(action_data);
    case 'assigned':
      return formatAssignedChange(action_data);
    case 'priority_changed':
      return formatPriorityChange(action_data);
    case 'due_date_changed':
      return '修改了截止日期';
    case 'relation_added':
      return `添加了关联: ${action_data?.relation_type}`;
    case 'relation_removed':
      return '移除了关联';
    case 'attachment_added':
      return '添加了附件';
    case 'attachment_removed':
      return '移除了附件';
    case 'label_added':
      return '添加了标签';
    case 'label_removed':
      return '移除了标签';
    case 'reaction_added':
    case 'reaction_removed':
      return formatReactionAction(action_data, action_type);
    case 'resolved':
      return '标记为已解决';
    case 'closed':
      return '关闭了此 Issue';
    case 'reopened':
      return '重新打开此 Issue';
    default:
      return action_type;
  }
}

// Go back to list
function goBack() {
  router.push('/issue/list');
}

// Get relation label
function getRelationLabel(type: string): string {
  const labels: Record<string, string> = {
    blocks: '阻塞',
    is_blocked_by: '被阻塞',
    relates_to: '关联',
    duplicates: '重复',
    is_duplicated_by: '被重复',
    depends_on: '依赖',
    is_depended_by: '被依赖'
  };
  return labels[type] || type;
}

watch(
  issueId,
  id => {
    issueFocus.ensureDetailFocus(id);
  },
  { immediate: true }
);

watch(
  () => issue.value?.project_id,
  pid => {
    loadMilestones(pid);
  }
);

onMounted(() => {
  loadIssue();
  loadProjects();
  loadCycles();
});
</script>

<template>
  <div class="issue-detail-container">
    <NSpin :show="loading">
      <div v-if="issue" class="issue-detail-wrapper">
        <!-- Main Content (Left) -->
        <div class="main-content">
          <!-- Header -->
          <div class="issue-header">
            <div class="issue-title-row">
              <NButton quaternary @click="goBack">
                <template #icon>
                  <icon-mdi-arrow-left />
                </template>
              </NButton>
              <div class="issue-title-info">
                <div class="issue-code">{{ issue.issue_code }}</div>
                <h1 class="issue-title">{{ issue.title }}</h1>
                <div v-if="parentIssue || issue.parent_issue_id" class="parent-issue-link">
                  <NText depth="3" style="font-size: 12px">父 Issue：</NText>
                  <NButton
                    text
                    size="tiny"
                    type="primary"
                    @click="
                      router.push({
                        path: '/issue/detail',
                        query: { id: parentIssue?.id || issue.parent_issue_id }
                      })
                    "
                  >
                    {{ parentIssue?.issue_code || issue.parent_issue_id }}
                    <template v-if="parentIssue">· {{ parentIssue.title }}</template>
                  </NButton>
                </div>
              </div>
            </div>

            <!-- Quick Actions -->
            <div class="issue-actions">
              <NButtonGroup>
                <NButton size="small" @click="router.push({ path: '/issue/edit', query: { id: issue.id } })">
                  <template #icon>
                    <icon-mdi-pencil />
                  </template>
                  编辑
                </NButton>
                <NButton size="small" @click="startEdit('status', issue.status)">
                  <template #icon>
                    <icon-mdi:swap-horizontal />
                  </template>
                  状态
                </NButton>
                <NButton size="small" @click="handleDeleteIssue">
                  <template #icon>
                    <icon-mdi-delete />
                  </template>
                  删除
                </NButton>
              </NButtonGroup>
            </div>
          </div>

          <!-- Description -->
          <div class="issue-description">
            <div class="section-header">
              <NText strong>描述</NText>
            </div>
            <div class="description-content">
              <NEmpty v-if="!issue.description" description="暂无描述" size="small" />
              <MarkdownRenderer v-else :content="issue.description" />
            </div>

            <!-- Reactions -->
            <IssueReactions
              v-model="reactions"
              :current-user-id="currentUserId"
              @react="handleReact"
              @unreact="handleUnreact"
            />
          </div>

          <!-- Attachments -->
          <NCard class="attachment-card-compact" size="small" title="附件">
            <NSpin :show="attachmentsLoading">
              <AttachmentList :issue-id="issueId" :attachments="attachments" @refresh="loadAttachments" />
            </NSpin>
          </NCard>

          <!-- Comments & Timeline -->
          <div class="issue-activity">
            <div class="section-header">
              <NText strong>活动 ({{ timeline.length }})</NText>
            </div>

            <!-- Combined Timeline (Comments + Activities) -->
            <NSpin :show="commentsLoading || timelineLoading">
              <div v-if="comments.length > 0 || timeline.length > 0" class="activity-list">
                <!-- Comments -->
                <div v-for="comment in comments" :key="'comment-' + comment.id" class="activity-item comment">
                  <div class="activity-icon">
                    <icon-mdi-comment-text-outline />
                  </div>
                  <div class="activity-content">
                    <div class="activity-header">
                      <NSpace align="center" :size="8">
                        <NText strong>
                          {{ comment.user_info?.sso_name || comment.user_info?.name || comment.user_id }}
                        </NText>
                        <NText depth="3" style="font-size: 12px">
                          {{ formatDateTime(comment.created_at) }}
                        </NText>
                      </NSpace>
                      <NButton
                        v-if="comment.user_id === 'admin'"
                        text
                        size="tiny"
                        @click="handleDeleteComment(comment.id)"
                      >
                        删除
                      </NButton>
                    </div>
                    <div class="comment-text">
                      <MarkdownRenderer :content="comment.content" />
                    </div>
                  </div>
                </div>

                <!-- Timeline Activities (exclude commented, already shown above) -->
                <div v-for="item in nonCommentTimeline" :key="'timeline-' + item.id" class="activity-item timeline">
                  <div class="activity-icon">
                    <icon-mdi-clock-outline />
                  </div>
                  <div class="activity-content">
                    <div class="activity-header">
                      <NText depth="3" style="font-size: 12px">
                        {{ formatDateTime(item.created_at) }}
                      </NText>
                    </div>
                    <div class="timeline-text">
                      <NText v-if="item.user_info">{{ item.user_info.name || item.user_info.id }}</NText>
                      <NText v-else-if="item.user_id">{{ item.user_id }}</NText>
                      <NText depth="2">{{ formatTimelineAction(item) }}</NText>
                    </div>
                  </div>
                </div>
              </div>
              <NEmpty v-else description="暂无活动" size="small" />
            </NSpin>

            <!-- Add Comment -->
            <div class="add-comment">
              <MarkdownEditor
                v-model="newComment"
                placeholder="添加评论...支持 Markdown 语法。使用 @提及用户，+ISSUE-xxx 引用问题、+PROJECT-xxx 引用项目、+REQUIREMENT-xxx 引用需求等"
                :rows="4"
                @submit="handleAddComment"
              />
              <div class="comment-actions">
                <NButton type="primary" size="small" :disabled="!newComment.trim()" @click="handleAddComment">
                  发表评论
                </NButton>
              </div>
            </div>
          </div>
        </div>

        <!-- Sidebar (Right) -->
        <div class="sidebar">
          <NCard size="small" :bordered="false">
            <!-- Status -->
            <EditableField
              v-model="tempStatus"
              v-model:editing="editingStatus"
              label="状态"
              :display-value="statusOptions.find(s => s.value === issue.status)?.label || issue.status"
              :options="statusOptions"
              :tag-type="getStatusType(issue.status)"
              @save="saveStatus"
              @cancel="cancelStatus"
              @start-edit="tempStatus = issue.status"
            >
              <template #label-icon>
                <icon-mdi-checkbox-marked-circle />
              </template>
            </EditableField>

            <!-- Assignee -->
            <EditableField
              v-model="tempAssignee"
              v-model:editing="editingAssignee"
              label="负责人"
              :display-value="issue.assignee?.sso_name || issue.assignee?.name || issue.assignee_id || '未分配'"
              placeholder="未分配"
              @save="saveAssignee"
              @cancel="cancelAssignee"
              @start-edit="tempAssignee = issue.assignee_id || ''"
            >
              <template #label-icon>
                <icon-mdi-account />
              </template>
              <template #editor>
                <UserSelect
                  :model-value="tempAssignee"
                  placeholder="选择负责人"
                  size="small"
                  @update:model-value="
                    value => {
                      tempAssignee = value;
                    }
                  "
                />
              </template>
            </EditableField>

            <!-- Priority -->
            <EditableField
              v-model="tempPriority"
              v-model:editing="editingPriority"
              label="优先级"
              :display-value="priorityOptions.find(p => p.value === issue.priority)?.label || issue.priority"
              :options="priorityOptions"
              :tag-type="getPriorityType(issue.priority)"
              @save="savePriority"
              @cancel="cancelPriority"
              @start-edit="tempPriority = issue.priority || null"
            >
              <template #label-icon>
                <icon-mdi-flag />
              </template>
            </EditableField>

            <!-- Cycle -->
            <EditableField
              v-model="tempCycle"
              v-model:editing="editingCycle"
              label="Cycle"
              :display-value="cycleDisplayValue"
              placeholder="未分配"
              @save="saveCycle"
              @cancel="cancelCycle"
              @start-edit="tempCycle = issue.cycle_id || null"
            >
              <template #label-icon>
                <icon-mdi-repeat />
              </template>
              <template #editor>
                <NSelect
                  v-model:value="tempCycle"
                  :options="cycleOptions"
                  placeholder="选择 Cycle"
                  size="small"
                  clearable
                />
              </template>
            </EditableField>

            <!-- Milestone (E8-S1) -->
            <EditableField
              v-model="tempMilestone"
              v-model:editing="editingMilestone"
              label="Milestone"
              :display-value="milestoneDisplayValue"
              placeholder="未分配"
              @save="saveMilestone"
              @cancel="cancelMilestone"
              @start-edit="tempMilestone = issue.milestone_id || null"
            >
              <template #label-icon>
                <icon-mdi-flag-checkered />
              </template>
              <template #editor>
                <NSelect
                  v-model:value="tempMilestone"
                  :options="milestoneOptions"
                  placeholder="选择 Milestone"
                  size="small"
                  clearable
                />
              </template>
            </EditableField>

            <!-- Type -->
            <EditableField
              v-model="tempType"
              v-model:editing="editingType"
              label="类型"
              :display-value="typeOptions.find(t => t.value === issue.type)?.label || issue.type"
              :options="typeOptions"
              :tag-type="getTypeType(issue.type)"
              @save="saveType"
              @cancel="cancelType"
              @start-edit="tempType = issue.type"
            >
              <template #label-icon>
                <icon-mdi-tag />
              </template>
            </EditableField>

            <!-- Due Date -->
            <EditableField
              v-model="tempDueDate"
              v-model:editing="editingDueDate"
              label="截止日期"
              :display-value="formatDate(issue.due_date)"
              placeholder="-"
              @save="saveDueDate"
              @cancel="cancelDueDate"
              @start-edit="tempDueDate = issue.due_date ? Number(new Date(issue.due_date).getTime() / 1000) : null"
            >
              <template #label-icon>
                <icon-mdi-calendar />
              </template>
              <template #editor>
                <NDatePicker v-model:value="tempDueDate" type="date" size="small" />
              </template>
            </EditableField>

            <!-- Reporter -->
            <EditableField
              v-model="tempReporter"
              v-model:editing="editingReporter"
              label="报告人"
              :display-value="issue.reporter?.sso_name || issue.reporter?.name || issue.reporter_id || '未设置'"
              placeholder="未设置"
              @save="saveReporter"
              @cancel="cancelReporter"
              @start-edit="tempReporter = issue.reporter_id || ''"
            >
              <template #label-icon>
                <icon-mdi-account-circle />
              </template>
              <template #editor>
                <UserSelect
                  :model-value="tempReporter"
                  placeholder="选择报告人"
                  size="small"
                  @update:model-value="
                    value => {
                      tempReporter = value;
                    }
                  "
                />
              </template>
            </EditableField>

            <!-- Project -->
            <EditableField
              v-model="tempProject"
              v-model:editing="editingProject"
              label="项目"
              :display-value="issue.project?.name || ''"
              :options="projectOptions"
              placeholder="未设置"
              select-width="140px"
              :clearable="true"
              @save="saveProject"
              @cancel="cancelProject"
              @start-edit="tempProject = issue.project_id || ''"
            >
              <template #label-icon>
                <icon-mdi-folder />
              </template>
            </EditableField>

            <!-- Time Tracking -->
            <div v-if="issue.estimated_hours || issue.actual_hours" class="sidebar-field">
              <div class="field-label">
                <icon-mdi-clock-outline />
                工时
              </div>
              <div class="field-value">
                <NText v-if="issue.estimated_hours">预估: {{ issue.estimated_hours }}h</NText>
                <NText v-if="issue.actual_hours" style="margin-left: 8px">实际: {{ issue.actual_hours }}h</NText>
              </div>
            </div>

            <!-- Linked Issues -->
            <div
              v-if="relations && (relations.as_source.length > 0 || relations.as_target.length > 0)"
              class="sidebar-section"
            >
              <div class="sidebar-section-title">关联 Issue</div>
              <div class="linked-issues">
                <div
                  v-for="(rel, idx) in relations.as_source"
                  :key="'source-' + idx + '-' + rel.target_id"
                  class="linked-issue"
                >
                  <NTag size="tiny" :bordered="false">{{ getRelationLabel(rel.relation_type) }}</NTag>
                  <NButton
                    text
                    size="tiny"
                    @click="router.push({ path: '/issue/detail', query: { id: rel.target_id } })"
                  >
                    {{ rel.target_issue?.issue_code || rel.target_id }}
                  </NButton>
                </div>
                <div
                  v-for="(rel, idx) in relations.as_target"
                  :key="'target-' + idx + '-' + rel.source_id"
                  class="linked-issue"
                >
                  <NTag size="tiny" :bordered="false">{{ getRelationLabel(rel.relation_type) }}</NTag>
                  <NButton
                    text
                    size="tiny"
                    @click="router.push({ path: '/issue/detail', query: { id: rel.source_id } })"
                  >
                    {{ rel.source_issue?.issue_code || rel.source_id }}
                  </NButton>
                </div>
              </div>
            </div>

            <!-- Tags -->
            <div class="sidebar-section">
              <div class="sidebar-section-title">
                <span>标签</span>
                <NButton text size="tiny" @click="showAddTag = !showAddTag">+ 添加</NButton>
              </div>
              <div class="tags-list">
                <NTag
                  v-for="(tag, idx) in tags"
                  :key="'tag-' + idx + '-' + (tag.id ?? tag.tag_id)"
                  size="small"
                  closable
                  :bordered="false"
                  :style="{ background: tagDisplayColor(tag), color: '#fff' }"
                  @close="handleRemoveTag(tag)"
                >
                  {{ tagDisplayName(tag) }}
                </NTag>
                <NText v-if="!tags.length" depth="3" style="font-size: 12px">暂无标签</NText>
              </div>
              <div v-if="showAddTag" class="mt-2">
                <NSelect
                  v-model:value="pendingTagId"
                  :options="availableTags.map(t => ({ label: t.name, value: t.id }))"
                  placeholder="选择标签"
                  size="small"
                  filterable
                  clearable
                />
                <NButton
                  class="mt-2"
                  size="tiny"
                  type="primary"
                  :disabled="pendingTagId === null"
                  @click="handleAddTag"
                >
                  确认添加
                </NButton>
              </div>
            </div>

            <!-- Metadata -->
            <div class="sidebar-section metadata">
              <div class="metadata-item">
                <NText depth="3" style="font-size: 11px">创建于 {{ formatDateTime(issue.created_at) }}</NText>
              </div>
              <div class="metadata-item">
                <NText depth="3" style="font-size: 11px">更新于 {{ formatDateTime(issue.updated_at) }}</NText>
              </div>
              <div class="metadata-item">
                <NText depth="3" style="font-size: 11px">浏览 {{ issue.view_count }} 次</NText>
              </div>
            </div>
          </NCard>

          <!-- 快速操作卡片 -->
          <NCard size="small" :bordered="false" class="mb-4">
            <template #header>
              <div class="card-header">
                <span class="card-icon">⚡</span>
                <span>快速操作</span>
              </div>
            </template>

            <NSpace vertical :size="8">
              <NButton block secondary type="info" @click="showAgentPrompt">
                <span class="action-icon">📋</span>
                获取 Agent 指令
              </NButton>

              <NButton block secondary @click="refreshData">
                <span class="action-icon">🔄</span>
                刷新数据
              </NButton>
            </NSpace>
          </NCard>
        </div>
      </div>

      <NEmpty v-else-if="!loading" description="Issue 不存在" size="large" />
    </NSpin>

    <!-- Agent Prompt Modal -->
    <NModal v-model:show="showAddSubIssue" preset="card" title="添加子 Issue" style="width: 480px">
      <NSpace vertical>
        <NText depth="3">将创建挂在当前 Issue 下的子项（parent_issue_id）。</NText>
        <NInput v-model:value="newSubIssueTitle" placeholder="子 Issue 标题" @keyup.enter="createSubIssue" />
        <NSpace justify="end">
          <NButton @click="showAddSubIssue = false">取消</NButton>
          <NButton type="primary" :loading="addingSubIssue" @click="createSubIssue">创建</NButton>
        </NSpace>
      </NSpace>
    </NModal>

    <NModal v-model:show="showAgentPromptModal" preset="card" title="🤖 Agent 工作指令" style="width: 700px">
      <NAlert type="success" class="mb-3">复制下方指令，粘贴到 Claude 中即可指挥 agent 开始工作</NAlert>

      <div class="agent-prompt-modal-content">
        <div class="prompt-actions">
          <NButton type="primary" @click="copyIssuePrompt">
            <template #icon>
              <icon-mdi-content-copy />
            </template>
            复制指令
          </NButton>
        </div>

        <div class="prompt-display">
          <pre class="prompt-code">{{ generateIssueAgentPrompt() }}</pre>
        </div>
      </div>
    </NModal>
  </div>
</template>

<style scoped>
/* ============================================
   DESIGN TOKENS - 紧凑现代风格
   ============================================ */
.issue-detail-container {
  padding: var(--space-md);
  width: 100%;
  max-width: 100%;
  background: var(--color-bg-secondary);
  min-height: 100vh;
}

/* ============================================
   LAYOUT - 紧凑布局
   ============================================ */
.issue-detail-wrapper {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--space-lg);
  align-items: start;
  max-width: 1400px;
  margin: 0 auto;
}

.main-content {
  min-width: 0;
}

/* ============================================
   ISSUE HEADER - 紧凑风格
   ============================================ */
.issue-header {
  background: var(--color-bg-primary);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-md);
  border: 1px solid var(--color-border-subtle);
  transition: box-shadow 0.2s ease;
}

.issue-header:hover {
  box-shadow: var(--shadow-md);
}

.issue-title-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.issue-title-info {
  flex: 1;
}

.issue-code {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-sm);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.issue-code::before {
  content: '';
  width: 8px;
  height: 8px;
  background: var(--color-primary);
  border-radius: 50%;
  display: inline-block;
}

.parent-issue-link {
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.issue-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
  line-height: 1.3;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.issue-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
}

/* ============================================
   CARDS - Description & Activity - 紧凑风格
   ============================================ */
.issue-description,
.issue-activity {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  margin-bottom: var(--space-md);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease;
}

.issue-description:hover,
.issue-activity:hover {
  box-shadow: var(--shadow-md);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border-subtle);
  font-weight: 600;
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
}

.description-content {
  min-height: 80px;
  color: var(--color-text-primary);
}

/* 描述和评论使用相同样式 */
.description-content,
.comment-text {
  word-break: break-word;
  line-height: 1.6;
  font-size: 14px;
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: -0.01em;
}

/* 确保 MarkdownRenderer 内部样式不被覆盖 */
.description-content :deep(.markdown-body),
.comment-text :deep(.markdown-body) {
  white-space: normal;
}

/* ============================================
   COMMENTS - Enhanced
   ============================================ */
.add-comment {
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border-subtle);
}

/* ============================================
   ATTACHMENTS - Compact Style
   ============================================ */
.attachment-card-compact {
  margin-bottom: var(--space-md);
}

.attachment-card-compact :deep(.n-card__content) {
  padding: var(--space-sm) !important;
}

.comment-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--space-md);
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.activity-item {
  display: flex;
  gap: var(--space-md);
  animation: slideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.activity-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-full);
  font-size: 16px;
  border: 2px solid var(--color-bg-primary);
  transition: transform 0.2s ease;
}

.activity-item:hover .activity-icon {
  transform: scale(1.05);
}

.activity-content {
  flex: 1;
  min-width: 0;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-sm);
}

.comment-text {
  word-break: break-word;
  line-height: 1.6;
  font-size: 14px;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

/* 确保 markdown 样式不受父容器影响 */
.comment-text :deep(.markdown-body) {
  white-space: normal;
}

.timeline-text {
  color: var(--color-text-secondary);
  font-size: 14px;
}

/* ============================================
   SIDEBAR - 紧凑风格
   ============================================ */
.sidebar {
  position: sticky;
  top: var(--space-md);
  max-height: calc(100vh - var(--space-lg));
  overflow-y: auto;
  overflow-x: hidden;
}

/* Custom Scrollbar */
.sidebar::-webkit-scrollbar {
  width: 6px;
}

.sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: var(--radius-full);
}

.sidebar::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-tertiary);
}

.sidebar-card {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-lg);
  transition: box-shadow 0.2s ease;
}

.sidebar-card:hover {
  box-shadow: var(--shadow-md);
}

/* Sidebar Sections */
.sidebar-section {
  padding: var(--space-md) 0;
  border-top: 2px solid var(--color-border-subtle);
  margin-top: var(--space-md);
}

.sidebar-section:first-of-type {
  border-top: none;
  margin-top: 0;
  padding-top: 0;
}

.sidebar-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-md);
  text-transform: none;
  letter-spacing: 0;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.linked-issues {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.linked-issue {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 14px;
  padding: var(--space-sm);
  border-radius: var(--radius-md);
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  text-decoration: none;
  color: inherit;
}

.linked-issue:hover {
  background: var(--color-bg-hover);
  transform: translateX(4px);
}

.metadata {
  border-top: 1px solid var(--color-border-subtle);
  padding-top: var(--space-md);
  margin-top: var(--space-md);
}

.metadata-item {
  margin-bottom: var(--space-sm);
  font-size: 13px;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.metadata-item::before {
  content: '•';
  color: var(--color-border-strong);
}

/* ============================================
   RESPONSIVE DESIGN
   ============================================ */
@media (max-width: 1200px) {
  .issue-detail-wrapper {
    grid-template-columns: 1fr 300px;
    gap: var(--space-xl);
  }
}

@media (max-width: 1024px) {
  .issue-detail-wrapper {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: static;
    max-height: none;
  }

  .issue-title {
    font-size: 24px;
  }
}

@media (max-width: 768px) {
  .issue-detail-container {
    padding: var(--space-md);
  }

  .issue-header {
    padding: var(--space-lg);
  }

  .issue-title {
    font-size: 20px;
  }

  .issue-description,
  .issue-activity {
    padding: var(--space-lg);
  }
}

/* ============================================
   ACCESSIBILITY
   ============================================ */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Focus Styles */
*:focus-visible {
  outline: 2px solid var(--color-accent-primary);
  outline-offset: 2px;
}

/* High Contrast Mode */
@media (prefers-contrast: high) {
  .issue-detail-container {
    --color-border-subtle: #000;
    --color-text-secondary: #000;
  }
}

/* Agent Prompt Modal Styles */
.mb-3 {
  margin-bottom: 12px;
}

.agent-prompt-modal-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.prompt-actions {
  display: flex;
  justify-content: flex-end;
}

.prompt-display {
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.prompt-display::-webkit-scrollbar {
  width: 8px;
}

.prompt-display::-webkit-scrollbar-thumb {
  background: #4b5563;
  border-radius: 4px;
}

.prompt-display::-webkit-scrollbar-track {
  background: #1f2937;
}

.prompt-code {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-border-subtle);
}
</style>
