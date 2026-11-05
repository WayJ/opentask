
/** E28：拼导出 query（与列表常用过滤对齐） */
export function buildIssueExportParams(filters: Record<string, unknown> = {}) {
  const allowed = ['status', 'priority', 'type', 'project_id', 'assignee_id', 'cycle_id', 'search'] as const;
  const out: Record<string, string> = {};
  for (const key of allowed) {
    const v = filters[key];
    if (v !== undefined && v !== null && v !== '') out[key] = String(v);
  }
  return out;
}

/** E28：格式化导入结果摘要 */
export function formatIssueImportSummary(data: {
  created?: number;
  updated?: number;
  errors?: { row: number; message: string }[];
}) {
  const created = data.created ?? 0;
  const updated = data.updated ?? 0;
  const errors = data.errors ?? [];
  const base = `创建 ${created} · 更新 ${updated}`;
  if (!errors.length) return base;
  const first = errors.slice(0, 3).map(e => `行${e.row}: ${e.message}`).join('；');
  const more = errors.length > 3 ? ` 等 ${errors.length} 条错误` : '';
  return `${base} · 错误 ${errors.length}（${first}${more}）`;
}

/** Issue API 客户端 */
import { downloadRequest, request } from '@/service/request';
import type { Api } from '@/typings/api';

/**
 * 清理请求参数，移除空值、null 和 undefined
 */
function cleanParams(params: Record<string, any>): Record<string, any> {
  return Object.fromEntries(Object.entries(params).filter(([_, v]) => v !== '' && v !== null && v !== undefined));
}

/** Build query params for issue detail; used by getIssue and unit-tested. */
export function buildIssueDetailParams(
  opts?: { byCode?: boolean; includeDeleted?: boolean }
): Record<string, true> | undefined {
  const params: Record<string, true> = {};
  if (opts?.byCode) params.by_code = true;
  if (opts?.includeDeleted) params.include_deleted = true;
  return Object.keys(params).length ? params : undefined;
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

  /** E28：导出 CSV（blob） */
  exportIssuesCsv: (params?: Record<string, unknown>) => {
    return downloadRequest<Blob>({
      url: '/api/issues/export.csv',
      method: 'GET',
      params: buildIssueExportParams(params || {}),
      responseType: 'blob'
    });
  },

  /** E28：导入模板 CSV */
  downloadImportTemplateCsv: () => {
    return downloadRequest<Blob>({
      url: '/api/issues/import/template.csv',
      method: 'GET',
      responseType: 'blob'
    });
  },

  /** E28：导入 CSV */
  importIssuesCsv: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<{ created: number; updated: number; errors: { row: number; message: string }[] }>({
      url: '/api/issues/import',
      method: 'POST',
      data: form
    });
  },

  /**
   * 获取 Issue 详情
   * @param opts.byCode 为 true 时按 issue_code 查询（?by_code=true）
   */
  getIssue: (id: string, opts?: { byCode?: boolean; includeDeleted?: boolean }) => {
    return request<Api.Issue.Issue>({
      url: `/api/issues/${id}`,
      method: 'GET',
      params: buildIssueDetailParams(opts)
    });
  },

  /** E77: list soft-deleted Issues */
  listTrash: (params?: { page?: number; page_size?: number }) => {
    const cleanedParams = params ? cleanParams(params) : undefined;
    return request<Api.Issue.IssueListResponse['data']>({
      url: '/api/issues/trash',
      method: 'GET',
      params: cleanedParams
    });
  },

  /** E77: restore soft-deleted Issue */
  restoreIssue: (id: string) => {
    return request<Api.Issue.Issue>({
      url: `/api/issues/${id}/restore`,
      method: 'POST'
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
   * E75: 复制 Issue（Linear-style duplicate）
   */
  duplicateIssue: (
    id: string,
    data?: {
      title?: string;
      project_id?: string | null;
      cycle_id?: string | null;
      parent_issue_id?: string | null;
      assignee_ids?: string[];
    }
  ) => {
    return request<Api.Issue.Issue>({
      url: `/api/issues/${id}/duplicate`,
      method: 'POST',
      data: data || {}
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

  /** 整体替换标签（L picker） */
  replaceTags: (issueId: string, tagIds: number[]) => {
    return request<{
      rows: Api.Issue.IssueTag[];
      total: number;
    }>({
      url: `/api/issues/${issueId}/tags`,
      method: 'PUT',
      data: { tag_ids: tagIds }
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

  /** E47/E52：工作区 Activity Feed */
  fetchWorkspaceActivity: (params?: Record<string, unknown>) => {
    return request<{
      items: Array<{
        id: string;
        issueId: string;
        issueCode?: string | null;
        issueTitle?: string | null;
        actionType: string;
        actor?: { id: string; username?: string | null; displayName?: string | null } | null;
        createdAt?: string | null;
        payload?: Record<string, unknown> | null;
        reactions?: {
          scope: 'issue' | 'comment';
          commentId?: string | null;
          summary: Array<{ emoji: string; count: number; myReacted: boolean }>;
        } | null;
      }>;
      nextCursor: string | null;
    }>({
      url: '/api/issues/activity',
      method: 'GET',
      params: cleanParams(params || {})
    });
  },

  /** E52：薄铃铛未读数 */
  fetchActivityUnreadCount: (params?: { watching?: boolean }) => {
    return request<{ count: number; capped: boolean }>({
      url: '/api/issues/activity/unread-count',
      method: 'GET',
      params: cleanParams({ watching: params?.watching ?? true })
    });
  },

  /** E52：打开 Feed 标记已读 */
  markActivityRead: (body?: { watching?: boolean }) => {
    return request<{ lastSeenAt?: string | null; lastSeenId?: string }>({
      url: '/api/issues/activity/mark-read',
      method: 'POST',
      data: body ?? { watching: true }
    });
  },

  /** E41：单 Issue timeline CSV */
  exportTimelineCsv: (issueId: string, params?: Record<string, unknown>) => {
    return downloadRequest<Blob>({
      url: `/api/issues/${issueId}/timeline/export.csv`,
      method: 'GET',
      params,
      responseType: 'blob'
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

  getCommentReactions: (issueId: string, commentId: string) => {
    return request<{ reactions: Record<string, string[]> }>({
      url: `/api/issues/${issueId}/comments/${commentId}/reactions`,
      method: 'GET'
    });
  },

  addCommentReaction: (issueId: string, commentId: string, emoji: string) => {
    return request<{ reaction_id: number; reactions: Record<string, string[]> }>({
      url: `/api/issues/${issueId}/comments/${commentId}/reactions`,
      method: 'POST',
      data: { emoji }
    });
  },

  removeCommentReaction: (issueId: string, commentId: string, emoji: string) => {
    return request<{ reactions: Record<string, string[]> }>({
      url: `/api/issues/${issueId}/comments/${commentId}/reactions`,
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

  /** E69: list comment attachments */
  getCommentAttachments: (issueId: string, commentId: string) => {
    return request<Api.Document.Response[]>({
      url: `/api/issues/${issueId}/comments/${commentId}/attachments`,
      method: 'GET'
    });
  },

  /** E69: upload attachment onto a comment */
  uploadCommentAttachment: (issueId: string, commentId: string, data: { file: File; description?: string }) => {
    const formData = new FormData();
    formData.append('file', data.file);
    if (data.description) {
      formData.append('description', data.description);
    }
    return request<Api.Document.Response>({
      url: `/api/issues/${issueId}/comments/${commentId}/attachments`,
      method: 'POST',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  /** E69: delete comment attachment */
  deleteCommentAttachment: (issueId: string, commentId: string, attachmentId: string) => {
    return request({
      url: `/api/issues/${issueId}/comments/${commentId}/attachments/${attachmentId}`,
      method: 'DELETE'
    });
  },

  /**
   * E66: 签发短 TTL 签名 URL（预览/下载内联用；须成员会话）
   */
  createAttachmentSignedUrl: (
    attachmentId: string,
    purpose: 'download' | 'preview',
    ttlSeconds?: number
  ) => {
    return request<{ url: string; expiresAt: string }>({
      url: `/api/attachments/${attachmentId}/signed-url`,
      method: 'POST',
      data: {
        purpose,
        ...(ttlSeconds != null ? { ttlSeconds } : {})
      }
    });
  },

  /**
   * E66: 鉴权会话下载附件为 Blob（显式「下载」按钮）
   */
  downloadAttachmentBlob: (attachmentId: string) => {
    return downloadRequest<Blob>({
      url: `/api/attachments/${attachmentId}/download`,
      method: 'GET',
      responseType: 'blob'
    });
  },

  /**
   * @deprecated E66: 裸公共 URL 已废除；请用 createAttachmentSignedUrl / downloadAttachmentBlob
   */
  getAttachmentDownloadUrl: (_issueId: string, attachmentId: string) => {
    return `/api/attachments/${attachmentId}/download`;
  },

  /** E18: list issue watchers */
  listWatchers: (issueId: string) => {
    return request<Array<{ id: string; workspace_id: string; issue_id: string; user_id: string }>>({
      url: `/api/issues/${issueId}/watchers`,
      method: 'GET'
    });
  },

  /** E18: watch issue */
  watch: (issueId: string) => {
    return request<{ id: string; workspace_id: string; issue_id: string; user_id: string }>({
      url: `/api/issues/${issueId}/watchers`,
      method: 'POST'
    });
  },

  /** E18: unwatch issue */
  unwatch: (issueId: string) => {
    return request({
      url: `/api/issues/${issueId}/watchers`,
      method: 'DELETE'
    });
  }
};

export function fetchIssueWatchers(issueId: string) {
  return issueApi.listWatchers(issueId);
}

export function watchIssue(issueId: string) {
  return issueApi.watch(issueId);
}

export function unwatchIssue(issueId: string) {
  return issueApi.unwatch(issueId);
}
