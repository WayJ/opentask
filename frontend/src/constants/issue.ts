/**
 * Issue 类型常量
 */
export enum IssueTypeEnum {
  Bug = 'bug',
  Feature = 'feature',
  Question = 'question',
  Feedback = 'feedback',
  Incident = 'incident',
  Improvement = 'improvement'
}

/**
 * Issue 类型选项（用于下拉选择）
 */
export const issueTypeOptions = [
  { label: '缺陷', value: IssueTypeEnum.Bug },
  { label: '功能', value: IssueTypeEnum.Feature },
  { label: '问题', value: IssueTypeEnum.Question },
  { label: '反馈', value: IssueTypeEnum.Feedback },
  { label: '事件', value: IssueTypeEnum.Incident },
  { label: '改进', value: IssueTypeEnum.Improvement }
];

/**
 * Issue 类型标签类型映射
 */
export const issueTypeTagTypeMap: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  bug: 'error',
  feature: 'info',
  question: 'default',
  feedback: 'default',
  incident: 'error',
  improvement: 'success'
};

/**
 * 获取 Issue 类型标签类型
 */
export function getIssueTypeTagType(
  type: Api.Issue.IssueType | string
): 'default' | 'info' | 'success' | 'warning' | 'error' {
  return issueTypeTagTypeMap[type] || 'default';
}

/**
 * Issue 状态常量
 */
export enum IssueStatusEnum {
  Open = 'open',
  InProgress = 'in_progress',
  Feedback = 'feedback',
  Resolved = 'resolved',
  Closed = 'closed',
  Rejected = 'rejected'
}

/**
 * Issue 状态选项（用于下拉选择）
 */
export const issueStatusOptions = [
  { label: '待办', value: IssueStatusEnum.Open },
  { label: '进行中', value: IssueStatusEnum.InProgress },
  { label: '等待反馈', value: IssueStatusEnum.Feedback },
  { label: '已解决', value: IssueStatusEnum.Resolved },
  { label: '已关闭', value: IssueStatusEnum.Closed },
  { label: '已拒绝', value: IssueStatusEnum.Rejected }
];

/**
 * Issue 状态标签类型映射
 */
export const issueStatusTagTypeMap: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  open: 'default',
  in_progress: 'info',
  feedback: 'warning',
  resolved: 'success',
  closed: 'default',
  rejected: 'error'
};

/**
 * 获取 Issue 状态标签类型
 */
export function getIssueStatusTagType(
  status: Api.Issue.IssueStatus | string
): 'default' | 'info' | 'success' | 'warning' | 'error' {
  return issueStatusTagTypeMap[status] || 'default';
}

/**
 * Issue 优先级常量
 */
export enum IssuePriorityEnum {
  Low = 'low',
  Medium = 'medium',
  High = 'high',
  Critical = 'critical'
}

/**
 * Issue 优先级选项（用于下拉选择）
 */
export const issuePriorityOptions = [
  { label: '低', value: IssuePriorityEnum.Low },
  { label: '中', value: IssuePriorityEnum.Medium },
  { label: '高', value: IssuePriorityEnum.High },
  { label: '紧急', value: IssuePriorityEnum.Critical }
];

/**
 * Issue 优先级标签类型映射
 */
export const issuePriorityTagTypeMap: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  low: 'info',
  medium: 'default',
  high: 'warning',
  critical: 'error'
};

/**
 * 获取 Issue 优先级标签类型
 */
export function getIssuePriorityTagType(
  priority: Api.Issue.IssuePriority | string
): 'default' | 'info' | 'success' | 'warning' | 'error' {
  return issuePriorityTagTypeMap[priority] || 'default';
}

export function getIssuePriorityLabel(priority: Api.Issue.IssuePriority | string): string {
  return issuePriorityOptions.find(o => o.value === priority)?.label || String(priority || '');
}

/**
 * Issue 关系类型常量
 */
export enum RelationTypeEnum {
  Blocks = 'blocks',
  IsBlockedBy = 'is_blocked_by',
  RelatesTo = 'relates_to',
  Duplicates = 'duplicates',
  IsDuplicatedBy = 'is_duplicated_by',
  DependsOn = 'depends_on',
  IsDependedBy = 'is_depended_by'
}

/**
 * Issue 关系类型选项（用于下拉选择）
 */
export const relationTypeOptions = [
  { label: '阻塞', value: RelationTypeEnum.Blocks },
  { label: '被阻塞', value: RelationTypeEnum.IsBlockedBy },
  { label: '关联', value: RelationTypeEnum.RelatesTo },
  { label: '重复', value: RelationTypeEnum.Duplicates },
  { label: '被重复', value: RelationTypeEnum.IsDuplicatedBy },
  { label: '依赖', value: RelationTypeEnum.DependsOn },
  { label: '被依赖', value: RelationTypeEnum.IsDependedBy }
];

/**
 * Issue 关系类型标签映射
 */
export const relationTypeLabelMap: Record<string, string> = {
  blocks: '阻塞',
  is_blocked_by: '被阻塞',
  relates_to: '关联',
  duplicates: '重复',
  is_duplicated_by: '被重复',
  depends_on: '依赖',
  is_depended_by: '被依赖'
};

/**
 * 获取 Issue 关系类型标签
 */
export function getRelationTypeLabel(relationType: Api.Issue.RelationType | string): string {
  return relationTypeLabelMap[relationType] || relationType;
}
