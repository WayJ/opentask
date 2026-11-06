/**
 * OAuth 客户端管理纯函数（表单校验 / 展示映射）
 *
 * 后端口径（真源）：
 * - redirect_uri 白名单**精确匹配**（`backend/opentask/services/oauth2/client_service.py` `verify_redirect_uri`）；
 * - provider 支持的 scope 清单 = `backend/opentask/api/oauth2/read_api.py` 各端点
 *   `require_oauth_scope(...)` 的取值（4 个）；
 * - scope 允许集是**上界**，超出即 invalid_scope（不隐式收敛）。
 */

/** provider 实际支持的 scope 目录（真源：backend/opentask/api/oauth2/read_api.py） */
export const KNOWN_OAUTH_SCOPES: ReadonlyArray<{ scope: string; label: string; endpoint: string }> = [
  { scope: 'read:tasks', label: '读取任务列表与详情', endpoint: 'GET /oauth2/api/tasks' },
  { scope: 'read:projects', label: '读取项目列表与详情', endpoint: 'GET /oauth2/api/projects' },
  { scope: 'read:requirements', label: '读取需求列表与详情', endpoint: 'GET /oauth2/api/requirements' },
  { scope: 'profile', label: '读取基本资料（用户名、姓名）', endpoint: 'GET /oauth2/userinfo' }
];

/** scope → 中文说明（未知 scope 回退展示原值，不静默吞掉） */
export function scopeLabel(scope: string): string {
  return KNOWN_OAUTH_SCOPES.find(item => item.scope === scope)?.label || scope;
}

/** scope → 对应只读数据面端点（未知返回空串） */
export function scopeEndpoint(scope: string): string {
  return KNOWN_OAUTH_SCOPES.find(item => item.scope === scope)?.endpoint || '';
}

/**
 * 回调地址输入 → 白名单列表：按行/逗号切分、去空白、去重、保序
 *
 * 输入侧解析宽进（多行粘贴友好），合法性由 validateRedirectUri 逐条把关。
 */
export function parseRedirectUriList(raw: string): string[] {
  if (!raw) return [];
  const seen: string[] = [];
  for (const item of raw.split(/[\n,]+/)) {
    const uri = item.trim();
    if (uri && !seen.includes(uri)) {
      seen.push(uri);
    }
  }
  return seen;
}

/** redirect_uri 合法性：必须是绝对 http(s) URL（与后端精确匹配口径一致，不支持通配） */
export function validateRedirectUri(uri: string): { valid: boolean; reason?: string } {
  if (!uri.trim()) {
    return { valid: false, reason: '不能为空' };
  }
  if (/[\s]/.test(uri)) {
    return { valid: false, reason: '不能包含空白字符' };
  }
  try {
    // eslint-disable-next-line no-new
    const parsed = new URL(uri);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return { valid: false, reason: '必须是 http(s) 绝对 URL' };
    }
    if (!parsed.hostname) {
      return { valid: false, reason: '缺少主机名' };
    }
    return { valid: true };
  } catch {
    return { valid: false, reason: '不是合法的绝对 URL（须带 http(s)://）' };
  }
}

/** scope 输入归一：字符串按空格/逗号切分，数组原样；去重、保序 */
export function normalizeScopeList(raw: string | string[]): string[] {
  const items = typeof raw === 'string' ? raw.split(/[,\s]+/) : raw;
  const seen: string[] = [];
  for (const item of items) {
    const scope = item.trim();
    if (scope && !seen.includes(scope)) {
      seen.push(scope);
    }
  }
  return seen;
}

/** 是否为已知 scope（决定复选框是否勾选 vs 自定义输入） */
export function isKnownScope(scope: string): boolean {
  return KNOWN_OAUTH_SCOPES.some(item => item.scope === scope);
}

/** 安装申请状态 → 展示文案 */
export const INSTALL_STATUS_LABELS: Record<string, string> = {
  PENDING: '待确认',
  APPROVED: '已批准（待小蓝兑换）',
  REJECTED: '已拒绝',
  EXPIRED: '已过期',
  CONSUMED: '已完成（密钥已交付）'
};

export function installStatusLabel(status: string): string {
  return INSTALL_STATUS_LABELS[status] || status;
}

/** client 状态 → 展示文案 */
export function clientStatusLabel(status: string): string {
  if (status === 'ACTIVE') return '启用';
  if (status === 'DISABLED') return '停用';
  return status;
}
