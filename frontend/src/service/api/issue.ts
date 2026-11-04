/** Issue API 客户端 */
import { request } from '@/service/request';
import type { Api } from '@/typings/api';

/**
 * 清理请求参数，移除空值、null 和 undefined
 */
function cleanParams(params: Record<string, any>): Record<string, any> {
  return Object.fromEntries(Object.entries(params).filter(([_, v]) => v !== '' && v !== null && v !== undefined));
}


/** Build query params for issue detail; used by getIssue and unit-tested. */
export function buildIssueDetailParams(opts?: { byCode?: boolean }): { by_code: true } | undefined {
  if (opts?.byCode) return { by_code: true };
  return undefined;
}

export const issueApi = {
  /**
   * 获取 Issue 列表
   */
  getIssues: (params?: Api.Issue.IssueQueryParams) => {
    // 清理空值参数，避免 URL 中出现 ?priority=&page=1 这样的情况
    const cleanedParams = params ? cleanParams(params) : undefined;

    return request<Api.Issue.IssueListResponse['data']>({
      url: '/api/issues',
      method: 'GET',
      params: cleanedParams
    });
  },

  /**
   * 获取 Issue 详情
   * @param opts.byCode 为 true 时按 issue_code 查询（?by_code=true）
   */
  getIssue: (id: string, opts?: { byCode?: boolean }) => {
    return request<Api.Issue.Issue>({
      url: `/api/issues/${id}`,
      method: 'GET',
      params: buildIssueDetailParams(opts)
    });
  },

  /**
   * 获取直接子 Issue（depth-1）
   */
  getChildren: (id: string) => {
    return request<{ rows: Api.Issue.IssueChildSummary[]; total: number }>({
      url: `/api/issues/${id}/children`,
      method: 'get'
    });
  },

  /**
   * 创建 Issue
   */
  createIssue: (data: Api.Issue.CreateIssue) => {
    return request<Api.Issue.Issue>({
      url: '/api/issues',
      method: 'POST',
      data
    });
  },

  /**
   * 更新 Issue
   */
  updateIssue: (id: string, data: Api.Issue.UpdateIssue) => {
    return request<Api.Issue.Issue>({
      url: `/api/issues/${id}`,
      method: 'PUT',
      data
    });
  },

  /**
   * 看板拖拽落盘（status + position，可选 ordered_ids）
   */
  moveOnBoard: (data: {
    issue_id: string;
    status: Api.Issue.IssueStatus;
    position: number;
    ordered_ids?: string[];
  }) => {
    return request<Api.Issue.Issue>({
      url: '/api/issues/board/move',
      method: 'POST',
      data
    });
  },

  /**
   * 删除 Issue
   */
  deleteIssue: (id: string) => {
    return request({
      url: `/api/issues/${id}`,
      method: 'DELETE'
    });
  },

  /**
   * 批量更新 Issue
   */
  bulkUpdateIssues: (data: Api.Issue.BulkUpdateIssues) => {
    return request<{ affected_rows: number }>({
      url: '/api/issues/bulk/update',
      method: 'POST',
      data
    });
  },

  /**
   * 批量删除 Issue
   */
  bulkDeleteIssues: (data: Api.Issue.BulkDeleteIssues) => {
    return request<{ affected_rows: number }>({
      url: '/api/issues/bulk/delete',
      method: 'POST',
      data
    });
  },

  /**
   * 获取 Issue 评论列表
   */
  getComments: (issueId: string) => {
    return request<{
      rows: Api.Issue.IssueComment[];
      total: number;
    }>({
      url: `/api/issues/${issueId}/comments`,
      method: 'GET'
    });
  },

  /**
   * 添加评论
   */
  addComment: (issueId: string, content: string, parentId?: string) => {
    return request<Api.Issue.IssueComment>({
      url: `/api/issues/${issueId}/comments`,
      method: 'POST',
      data: { content, parent_id: parentId }
    });
  },

  /**
   * 更新评论
   */
  updateComment: (commentId: string, content: string) => {
    return request<Api.Issue.IssueComment>({
      url: `/api/issues/comments/${commentId}`,
      method: 'PUT',
      data: { content }
    });
  },

  /**
   * 删除评论
   */
  deleteComment: (commentId: string) => {
    return request({
      url: `/api/issues/comments/${commentId}`,
      method: 'DELETE'
    });
  },

  /**
   * 获取 Issue 关系
   */
  getRelations: (issueId: string) => {
    return request<{
      as_source: Api.Issue.IssueRelation[];
      as_target: Api.Issue.IssueRelation[];
    }>({
      url: `/api/issues/${issueId}/relations`,
      method: 'GET'
    });
  },

  /**
   * 添加关系
   */
  addRelation: (issueId: string, targetId: string, relationType: Api.Issue.RelationType) => {
    return request<Api.Issue.IssueRelation>({
      url: `/api/issues/${issueId}/relations`,
      method: 'POST',
      params: { target_id: targetId, relation_type: relationType }
    });
  },

  /**
   * 移除关系
   */
  removeRelation: (issueId: string, targetId: string, relationType: Api.Issue.RelationType) => {
    return request({
      url: `/api/issues/${issueId}/relations`,
      method: 'DELETE',
      params: { target_id: targetId, relation_type: relationType }
    });
  },

  /**
   * 获取 Issue 标签
   */
  getTags: (issueId: string) => {
    return request<{
      rows: Api.Issue.IssueTag[];
      total: number;
    }>({
      url: `/api/issues/${issueId}/tags`,
      method: 'GET'
    });
  },

  /**
   * 添加标签
   */
  addTag: (issueId: string, tagId: number) => {
    return request<{ issue_tag_id: number }>({
      url: `/api/issues/${issueId}/tags/${tagId}`,
      method: 'POST'
    });
  },

  /**
   * 移除标签
   */
  removeTag: (issueId: string, tagId: number) => {
    return request({
      url: `/api/issues/${issueId}/tags/${tagId}`,
      method: 'DELETE'
    });
  },

  /**
   * 获取时间线
   */
  getTimeline: (issueId: string, limit = 50) => {
    return request<{
      rows: Api.Issue.IssueTimeline[];
      total: number;
    }>({
      url: `/api/issues/${issueId}/timeline`,
      method: 'GET',
      params: { limit }
    });
  },

  /**
   * 获取统计信息
   */
  getStatistics: (projectId?: string) => {
    return request<Api.Issue.IssueStatistics>({
      url: '/api/issues/statistics',
      method: 'GET',
      params: { project_id: projectId }
    });
  },

  /**
   * 快速更新状态
   */
  updateStatus: (issueId: string, status: Api.Issue.IssueStatus) => {
    return request<Api.Issue.Issue>({
      url: `/api/issues/${issueId}/status`,
      method: 'PUT',
      params: { status }
    });
  },

  /**
   * 快速更新负责人
   */
  updateAssignee: (issueId: string, assigneeId?: string) => {
    return request<Api.Issue.Issue>({
      url: `/api/issues/${issueId}/assignee`,
      method: 'PUT',
      params: { assignee_id: assigneeId }
    });
  },

  /**
   * 快速更新优先级
   */
  updatePriority: (issueId: string, priority: Api.Issue.IssuePriority) => {
    return request<Api.Issue.Issue>({
      url: `/api/issues/${issueId}/priority`,
      method: 'PUT',
      params: { priority }
    });
  },

  /**
   * 快速更新报告人
   */
  updateReporter: (issueId: string, reporterId?: string) => {
    return request<Api.Issue.Issue>({
      url: `/api/issues/${issueId}/reporter`,
      method: 'PUT',
      params: { reporter_id: reporterId }
    });
  },

  /**
   * 获取 Issue 反应列表
   */
  getReactions: (issueId: string) => {
    return request<{
      rows: Array<{ emoji: string; count: number; users: string[] }>;
      total: number;
    }>({
      url: `/api/issues/${issueId}/reactions`,
      method: 'GET'
    });
  },

  /**
   * 添加反应
   */
  addReaction: (issueId: string, emoji: string) => {
    return request<{ reaction_id: number }>({
      url: `/api/issues/${issueId}/reactions`,
      method: 'POST',
      data: { emoji }
    });
  },

  /**
   * 移除反应
   */
  removeReaction: (issueId: string, emoji: string) => {
    return request({
      url: `/api/issues/${issueId}/reactions`,
      method: 'DELETE',
      params: { emoji }
    });
  },

  /**
   * 批量获取 Issues（优化性能，避免 N+1 查询）
   */
  getIssuesByIds: (ids: string[]) => {
    return request<Api.Issue.IssueListResponse['data']>({
      url: '/api/issues/batch',
      method: 'POST',
      data: { ids }
    });
  },

  // ============================================================================
  // 附件操作
  // ============================================================================

  /**
   * 获取 Issue 附件列表
   */
  getAttachments: (issueId: string) => {
    return request<Api.Document.Response[]>({
      url: `/api/issues/${issueId}/attachments`,
      method: 'GET'
    });
  },

  /**
   * 上传附件到 Issue
   */
  uploadAttachment: (issueId: string, data: { file: File; description?: string }) => {
    const formData = new FormData();
    formData.append('file', data.file);
    if (data.description) {
      formData.append('description', data.description);
    }

    return request<Api.Document.Response>({
      url: `/api/issues/${issueId}/attachments`,
      method: 'POST',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  /**
   * 删除 Issue 附件
   */
  deleteAttachment: (issueId: string, attachmentId: string) => {
    return request({
      url: `/api/issues/${issueId}/attachments/${attachmentId}`,
      method: 'DELETE'
    });
  },

  /**
   * 获取附件下载链接（公共访问，无需认证）
   */
  getAttachmentDownloadUrl: (_issueId: string, attachmentId: string) => {
    // 使用独立的附件路由，不需要 issueId
    return `/api/attachments/${attachmentId}/download`;
  }
};
