/** E66: browser URL helpers for authenticated / signed attachment access. */

/** Prefix relative API paths with the vite proxy pattern `/opentask`. */
export function toBrowserAttachmentUrl(apiPath: string): string {
  if (!apiPath) return apiPath;
  if (/^https?:\/\//i.test(apiPath)) return apiPath;
  const path = apiPath.startsWith('/') ? apiPath : `/${apiPath}`;
  if (path.startsWith('/opentask/')) return path;
  return `/opentask${path}`;
}

/** Friendly copy for attachment 401/404 surfaces. */
export function attachmentAccessDeniedMessage(status: number): string {
  if (status === 401) return '未登录或登录已过期，请重新登录后再查看附件';
  if (status === 404) return '附件不存在或您没有权限访问';
  return '附件加载失败';
}

/** E69: flatten per-comment attachment summaries for lists / vitest. */
export type CommentAttachmentSummary = {
  id: string;
  file_name: string;
  file_size: number;
  file_type: string;
};

export function flattenCommentAttachments(
  comments: Array<{ id: string; attachments?: CommentAttachmentSummary[] | null }>
): Array<CommentAttachmentSummary & { commentId: string }> {
  const out: Array<CommentAttachmentSummary & { commentId: string }> = [];
  for (const c of comments) {
    for (const a of c.attachments || []) {
      out.push({
        commentId: c.id,
        id: a.id,
        file_name: a.file_name,
        file_size: a.file_size,
        file_type: a.file_type
      });
    }
  }
  return out;
}

/** Map thin comment attachment summary → Document.Response-shaped row for AttachmentList. */
export function commentAttachmentToDocument(
  summary: CommentAttachmentSummary,
  commentId: string
): {
  id: string;
  entity_type: string;
  entity_id: string;
  file_name: string;
  file_path: string;
  file_type: string;
  file_size: number;
  status: 'PUBLISHED';
  created_at: string;
  updated_at: string;
} {
  return {
    id: summary.id,
    entity_type: 'issue_comment',
    entity_id: commentId,
    file_name: summary.file_name,
    file_path: '',
    file_type: summary.file_type,
    file_size: summary.file_size,
    status: 'PUBLISHED',
    created_at: '',
    updated_at: ''
  };
}
