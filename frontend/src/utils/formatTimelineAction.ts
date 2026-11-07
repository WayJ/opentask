/** E41：Issue timeline action 文案（纯函数，便于 vitest） */

export type TimelineActionItem = {
  action_type: string;
  action_data?: Record<string, any> | null;
};

const STATUS_LABELS: Record<string, string> = {
  open: '待处理',
  in_progress: '进行中',
  feedback: '等待反馈',
  resolved: '已解决',
  closed: '已关闭',
  rejected: '已拒绝'
};

const PRIORITY_LABELS: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '紧急'
};

function getStatusLabel(status: string) {
  return STATUS_LABELS[status] || status;
}

function getPriorityLabel(priority: string) {
  return PRIORITY_LABELS[priority] || priority;
}

function formatUserInfo(user: any) {
  if (!user) return '未分配';
  if (typeof user === 'object') {
    return user.sso_name || user.name || user.sso_account || user.id || '未分配';
  }
  return String(user);
}

function displayVal(v: unknown): string {
  if (v === null || v === undefined || v === '') return '空';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

export function formatTimelineAction(item: TimelineActionItem): string {
  const { action_type, action_data } = item;
  const ad = action_data || {};

  switch (action_type) {
    case 'created':
      return '创建了此问题';
    case 'restored':
      return '从回收站恢复了此问题';
    case 'updated':
      return '更新了问题';
    case 'commented':
      return '添加了评论';
    case 'status_changed':
      return `将状态从 "${getStatusLabel(ad?.from || '')}" 改为 "${getStatusLabel(ad?.to || '')}"`;
    case 'assigned':
      return `将负责人从 "${formatUserInfo(ad?.from)}" 改为 "${formatUserInfo(ad?.to)}"`;
    case 'priority_changed':
      return `将优先级从 "${getPriorityLabel(ad?.from || '')}" 改为 "${getPriorityLabel(ad?.to || '')}"`;
    case 'due_date_changed':
      return '修改了截止日期';
    case 'start_date_changed':
      return '修改了计划开始日';
    case 'relation_added':
      return `添加了关联: ${ad?.relation_type}`;
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
      return `添加了反应 ${ad?.emoji || ''}`;
    case 'reaction_removed':
      return `移除了反应 ${ad?.emoji || ''}`;
    case 'resolved':
      return '标记为已解决';
    case 'closed':
      return '关闭了此问题';
    case 'reopened':
      return '重新打开此问题';
    case 'custom_field_changed': {
      const key = ad.fieldKey || ad.field_key || '';
      return `将自定义字段 ${key} 从 ${displayVal(ad.from)} 改为 ${displayVal(ad.to)}`;
    }
    case 'cycle_changed':
      return `将冲刺从 ${displayVal(ad.from)} 改为 ${displayVal(ad.to)}`;
    case 'estimate_changed':
      return `将估分从 ${displayVal(ad.from)} 改为 ${displayVal(ad.to)}`;
    case 'project_changed':
      return `将项目从 ${displayVal(ad.from)} 改为 ${displayVal(ad.to)}`;
    case 'sla_paused': {
      const name = ad.policyName || ad.policyId || 'SLA';
      const metric = ad.metric === 'first_response' ? '首响' : '状态';
      return `暂停了${metric} SLA（${name}）`;
    }
    case 'sla_resumed': {
      const name = ad.policyName || ad.policyId || 'SLA';
      const metric = ad.metric === 'first_response' ? '首响' : '状态';
      return `恢复了${metric} SLA（${name}）`;
    }
    default:
      return action_type;
  }
}
