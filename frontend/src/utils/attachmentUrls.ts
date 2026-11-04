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
