/** E66: browser URL helpers for authenticated / signed attachment access. */

interface AttachmentEnv {
  DEV?: boolean;
  VITE_HTTP_PROXY?: string;
  VITE_SERVICE_BASE_URL?: string;
}

/** Dev vite proxy keeps `/opentask`. A production base of `/` adds nothing. */
export function attachmentPrefixFromEnv(env: AttachmentEnv = import.meta.env): string {
  if (env.DEV && env.VITE_HTTP_PROXY === 'Y') return '/opentask';
  const service = env.VITE_SERVICE_BASE_URL || '';
  if (service.startsWith('/') && service !== '/') return service.replace(/\/$/, '');
  return '';
}

/**
 * Join a service base with an absolute API path.
 * A production base of `/` must stay a same-origin path. Concatenating `/` + `/api`
 * would become a protocol-relative URL (`//api`).
 */
export function browserServiceUrl(path: string, base = ''): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  if (!base || base === '/') return normalized;
  return `${base.replace(/\/$/, '')}${normalized}`;
}

/** Prefix relative API paths using the active service base. */
export function toBrowserAttachmentUrl(apiPath: string, env: AttachmentEnv = import.meta.env): string {
  if (!apiPath) return apiPath;
  if (/^https?:\/\//i.test(apiPath)) return apiPath;
  const path = apiPath.startsWith('/') ? apiPath : `/${apiPath}`;
  const prefix = attachmentPrefixFromEnv(env);
  if (!prefix) return path;
  if (path === prefix || path.startsWith(`${prefix}/`)) return path;
  return `${prefix}${path}`;
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
