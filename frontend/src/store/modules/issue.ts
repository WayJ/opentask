import { reactive, ref } from 'vue';
import { defineStore } from 'pinia';
import { issueApi } from '@/service/api/issue';

export const useIssueStore = defineStore('issue', () => {
  const issues = ref<Api.Issue.Issue[]>([]);
  const currentIssue = ref<Api.Issue.Issue | null>(null);
  const comments = ref<Api.Issue.IssueComment[]>([]);
  const relations = ref<{
    as_source: Api.Issue.IssueRelation[];
    as_target: Api.Issue.IssueRelation[];
  } | null>(null);
  const timeline = ref<Api.Issue.IssueTimeline[]>([]);
  const tags = ref<Api.Issue.IssueTag[]>([]);
  const statistics = ref<Api.Issue.IssueStatistics | null>(null);
  const loading = ref(false);
  const pagination = reactive({
    total: 0,
    page: 1,
    pageSize: 20
  });

  /**
   * 获取 Issue 列表
   */
  async function getIssues(params?: Api.Issue.IssueQueryParams) {
    loading.value = true;
    try {
      const response = await issueApi.getIssues({
        ...params,
        page: params?.page || pagination.page,
        page_size: params?.page_size || pagination.pageSize
      });
      const data = response.data;
      issues.value = data?.rows || [];
      pagination.total = data?.total || 0;
      pagination.page = data?.current || 1;
      pagination.pageSize = data?.pageSize || 20;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 获取 Issue 详情
   */
  async function getIssue(id: string) {
    loading.value = true;
    try {
      const response = await issueApi.getIssue(id);
      currentIssue.value = response.data;
      return response.data;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 创建 Issue
   */
  async function createIssue(data: Api.Issue.CreateIssue) {
    const response = await issueApi.createIssue(data);
    const issue = response.data;
    issues.value.unshift(issue);
    pagination.total += 1;
    return issue;
  }

  /**
   * 更新 Issue
   */
  async function updateIssue(id: string, data: Api.Issue.UpdateIssue) {
    const response = await issueApi.updateIssue(id, data);
    const issue = response.data;
    const index = issues.value.findIndex(i => i.id === id);
    if (index !== -1) {
      issues.value[index] = issue;
    }
    if (currentIssue.value?.id === id) {
      currentIssue.value = issue;
    }
    return issue;
  }

  /**
   * 删除 Issue
   */
  async function deleteIssue(id: string) {
    await issueApi.deleteIssue(id);
    issues.value = issues.value.filter(i => i.id !== id);
    pagination.total -= 1;
    if (currentIssue.value?.id === id) {
      currentIssue.value = null;
    }
  }

  /**
   * 批量更新 Issue
   */
  async function bulkUpdate(data: Api.Issue.BulkUpdateIssues) {
    const response = await issueApi.bulkUpdateIssues(data);
    const { affected_rows } = response.data;
    // 刷新列表
    await getIssues();
    return affected_rows;
  }

  /**
   * 批量删除 Issue
   */
  async function bulkDelete(data: Api.Issue.BulkDeleteIssues) {
    const response = await issueApi.bulkDeleteIssues(data);
    const { affected_rows } = response.data;
    // 刷新列表
    await getIssues();
    return affected_rows;
  }

  /**
   * 获取评论列表
   */
  async function getComments(issueId: string) {
    loading.value = true;
    try {
      const response = await issueApi.getComments(issueId);
      const { rows, total } = response.data;
      comments.value = rows || [];
      return { rows, total };
    } finally {
      loading.value = false;
    }
  }

  /**
   * 添加评论
   */
  async function addComment(issueId: string, content: string, parentId?: string) {
    const response = await issueApi.addComment(issueId, content, parentId);
    const comment = response.data;
    comments.value.push(comment);
    return comment;
  }

  /**
   * 更新评论
   */
  async function updateComment(commentId: string, content: string) {
    const response = await issueApi.updateComment(commentId, content);
    const comment = response.data;
    const index = comments.value.findIndex(c => c.id === commentId);
    if (index !== -1) {
      comments.value[index] = comment;
    }
    return comment;
  }

  /**
   * 删除评论
   */
  async function deleteComment(commentId: string) {
    await issueApi.deleteComment(commentId);
    comments.value = comments.value.filter(c => c.id !== commentId);
  }

  /**
   * 获取 Issue 关系
   */
  async function getRelations(issueId: string) {
    loading.value = true;
    try {
      const response = await issueApi.getRelations(issueId);
      relations.value = response.data;
      return response.data;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 添加关系
   */
  async function addRelation(issueId: string, targetId: string, relationType: Api.Issue.RelationType) {
    const response = await issueApi.addRelation(issueId, targetId, relationType);
    const relation = response.data;
    if (relations.value) {
      relations.value.as_source.push(relation);
    }
    return relation;
  }

  /**
   * 移除关系
   */
  async function removeRelation(issueId: string, targetId: string, relationType: Api.Issue.RelationType) {
    await issueApi.removeRelation(issueId, targetId, relationType);
    if (relations.value) {
      relations.value.as_source = relations.value.as_source.filter(
        r => !(r.target_id === targetId && r.relation_type === relationType)
      );
    }
  }

  /**
   * 获取标签
   */
  async function getTags(issueId: string) {
    loading.value = true;
    try {
      const response = await issueApi.getTags(issueId);
      const { rows } = response.data;
      tags.value = rows || [];
      return rows;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 添加标签
   */
  async function addTag(issueId: string, tagId: number) {
    const response = await issueApi.addTag(issueId, tagId);
    // 重新获取标签列表
    await getTags(issueId);
    return response.data;
  }

  /**
   * 移除标签
   */
  async function removeTag(issueId: string, tagId: number) {
    await issueApi.removeTag(issueId, tagId);
    tags.value = tags.value.filter(t => t.tag_id !== tagId);
  }

  /**
   * 获取 Issue 反应列表
   */
  async function getReactions(issueId: string) {
    try {
      const response = await issueApi.getReactions(issueId);

      // 转换为 Record<string, string[]> 格式
      const reactionsMap: Record<string, string[]> = {};
      const rows = response.data?.rows || [];
      for (const item of rows) {
        reactionsMap[item.emoji] = item.users;
      }

      return reactionsMap;
    } catch (error) {
      console.error('获取反应失败:', error);
      return {};
    }
  }

  /**
   * 添加反应
   */
  async function addReaction(issueId: string, emoji: string) {
    await issueApi.addReaction(issueId, emoji);
  }

  /**
   * 移除反应
   */
  async function removeReaction(issueId: string, emoji: string) {
    await issueApi.removeReaction(issueId, emoji);
  }

  /**
   * 获取时间线
   */
  async function getTimeline(issueId: string, limit = 50) {
    loading.value = true;
    try {
      const response = await issueApi.getTimeline(issueId, limit);
      const { rows } = response.data;
      timeline.value = rows || [];
      return rows;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 获取统计信息
   */
  async function getStatistics(projectId?: string) {
    loading.value = true;
    try {
      const response = await issueApi.getStatistics(projectId);
      statistics.value = response.data;
      return response.data;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 快速更新状态
   */
  async function updateStatus(issueId: string, status: Api.Issue.IssueStatus) {
    const response = await issueApi.updateStatus(issueId, status);
    const issue = response.data;
    const index = issues.value.findIndex(i => i.id === issueId);
    if (index !== -1) {
      issues.value[index] = issue;
    }
    if (currentIssue.value?.id === issueId) {
      currentIssue.value = issue;
    }
    return issue;
  }

  /**
   * 快速更新负责人
   */
  async function updateAssignee(issueId: string, assigneeId?: string) {
    const response = await issueApi.updateAssignee(issueId, assigneeId);
    const issue = response.data;
    const index = issues.value.findIndex(i => i.id === issueId);
    if (index !== -1) {
      issues.value[index] = issue;
    }
    if (currentIssue.value?.id === issueId) {
      currentIssue.value = issue;
    }
    return issue;
  }

  /**
   * 快速更新优先级
   */
  async function updatePriority(issueId: string, priority: Api.Issue.IssuePriority) {
    const response = await issueApi.updatePriority(issueId, priority);
    const issue = response.data;
    const index = issues.value.findIndex(i => i.id === issueId);
    if (index !== -1) {
      issues.value[index] = issue;
    }
    if (currentIssue.value?.id === issueId) {
      currentIssue.value = issue;
    }
    return issue;
  }

  /**
   * 快速更新报告人
   */
  async function updateReporter(issueId: string, reporterId?: string) {
    const response = await issueApi.updateReporter(issueId, reporterId);
    const issue = response.data;
    const index = issues.value.findIndex(i => i.id === issueId);
    if (index !== -1) {
      issues.value[index] = issue;
    }
    if (currentIssue.value?.id === issueId) {
      currentIssue.value = issue;
    }
    return issue;
  }

  return {
    issues,
    currentIssue,
    comments,
    relations,
    timeline,
    tags,
    statistics,
    loading,
    pagination,
    getIssues,
    getIssue,
    createIssue,
    updateIssue,
    deleteIssue,
    bulkUpdate,
    bulkDelete,
    getComments,
    addComment,
    updateComment,
    deleteComment,
    getRelations,
    addRelation,
    removeRelation,
    getTags,
    addTag,
    removeTag,
    getReactions,
    addReaction,
    removeReaction,
    getTimeline,
    getStatistics,
    updateStatus,
    updateAssignee,
    updatePriority,
    updateReporter
  };
});
