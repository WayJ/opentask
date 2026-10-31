/**
 * 需求状态常量（小写，与后端 API 保持一致）
 *
 * PGE 流程（AI Agent 开发场景）：
 * - planning: 规划中 - 需求正在规划，还未开始实现
 * - generating: 生成中 - AI正在生成代码/实现功能
 * - evaluating: 评审中 - 人工或AI正在评审生成的结果
 * - completed: 已完成 - 需求已完成实现和评审
 * - closed: 已关闭 - 需求已关闭
 * - archived: 已归档 - 需求已归档
 */
export enum RequirementStatusEnum {
  Planning = 'planning',
  Generating = 'generating',
  Evaluating = 'evaluating',
  Completed = 'completed',
  Closed = 'closed',
  Archived = 'archived'
}

/**
 * 需求状态选项（用于下拉选择）
 */
export const requirementStatusOptions = [
  { label: '规划中', value: RequirementStatusEnum.Planning },
  { label: '生成中', value: RequirementStatusEnum.Generating },
  { label: '评审中', value: RequirementStatusEnum.Evaluating },
  { label: '已完成', value: RequirementStatusEnum.Completed },
  { label: '已关闭', value: RequirementStatusEnum.Closed },
  { label: '已归档', value: RequirementStatusEnum.Archived }
];

/**
 * 需求状态文本映射（小写版本）
 */
export const requirementStatusTextMap: Record<string, string> = {
  planning: '规划中',
  generating: '生成中',
  evaluating: '评审中',
  completed: '已完成',
  closed: '已关闭',
  archived: '已归档'
};

/**
 * 获取需求状态文本（自动处理大小写转换和旧状态兼容）
 */
export function getRequirementStatusText(status: string): string {
  // 旧状态到新状态的映射（兼容旧数据）
  const legacyStatusMap: Record<string, string> = {
    draft: 'planning',
    clarifying: 'planning',
    spec_ready: 'planning',
    designing: 'planning',
    coding: 'generating',
    reviewing: 'evaluating',
    testing: 'evaluating',
    released: 'completed'
  };

  // 先尝试直接查找
  if (requirementStatusTextMap[status]) {
    return requirementStatusTextMap[status];
  }

  // 如果是旧状态，映射到新状态
  const mappedStatus = legacyStatusMap[status];
  if (mappedStatus && requirementStatusTextMap[mappedStatus]) {
    return requirementStatusTextMap[mappedStatus];
  }

  // 如果找不到，返回原始值
  return status;
}

/**
 * 需求状态标签类型映射（小写版本）
 */
export const requirementStatusTagTypeMap: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  planning: 'default',
  generating: 'warning',
  evaluating: 'info',
  completed: 'success',
  closed: 'default',
  archived: 'default'
};

/**
 * 获取需求状态标签类型（自动处理大小写转换和旧状态兼容）
 */
export function getRequirementStatusTagType(status: string): 'default' | 'info' | 'success' | 'warning' | 'error' {
  // 旧状态到新状态的映射（兼容旧数据）
  const legacyStatusMap: Record<string, string> = {
    draft: 'planning',
    clarifying: 'planning',
    spec_ready: 'planning',
    designing: 'planning',
    coding: 'generating',
    reviewing: 'evaluating',
    testing: 'evaluating',
    released: 'completed'
  };

  // 先尝试直接查找
  if (requirementStatusTagTypeMap[status]) {
    return requirementStatusTagTypeMap[status];
  }

  // 如果是旧状态，映射到新状态
  const mappedStatus = legacyStatusMap[status];
  if (mappedStatus && requirementStatusTagTypeMap[mappedStatus]) {
    return requirementStatusTagTypeMap[mappedStatus];
  }

  // 默认返回 default
  return 'default';
}

/**
 * 需求优先级常量（小写，与后端 API 保持一致）
 */
export enum RequirementPriorityEnum {
  Low = 'low',
  Medium = 'medium',
  High = 'high',
  Critical = 'critical'
}

/**
 * 需求优先级选项（用于下拉选择）
 */
export const requirementPriorityOptions = [
  { label: '低', value: RequirementPriorityEnum.Low },
  { label: '中', value: RequirementPriorityEnum.Medium },
  { label: '高', value: RequirementPriorityEnum.High },
  { label: '紧急', value: RequirementPriorityEnum.Critical }
];

/**
 * 需求优先级文本映射（小写版本）
 */
export const requirementPriorityTextMap: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '紧急'
};

/**
 * 获取需求优先级文本（自动处理大小写转换）
 */
export function getRequirementPriorityText(priority: string): string {
  // 先尝试直接查找
  if (requirementPriorityTextMap[priority]) {
    return requirementPriorityTextMap[priority];
  }

  // 如果找不到，尝试转换为小写后查找（兼容旧的大写值）
  const normalizedKey = priority.toLowerCase();
  return requirementPriorityTextMap[normalizedKey] || priority;
}

/**
 * 需求优先级标签类型映射（小写版本）
 */
export const requirementPriorityTagTypeMap: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  low: 'info',
  medium: 'default',
  high: 'warning',
  critical: 'error'
};

/**
 * 获取需求优先级标签类型（自动处理大小写转换）
 */
export function getRequirementPriorityTagType(
  priority: Api.Requirement.Priority | string
): 'default' | 'info' | 'success' | 'warning' | 'error' {
  // 先尝试直接查找
  if (requirementPriorityTagTypeMap[priority]) {
    return requirementPriorityTagTypeMap[priority];
  }

  // 如果找不到，尝试转换为小写后查找
  const normalizedKey = priority.toLowerCase();
  return requirementPriorityTagTypeMap[normalizedKey] || 'default';
}
