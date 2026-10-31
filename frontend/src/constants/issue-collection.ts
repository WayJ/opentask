/**
 * 问题集常量定义
 */

/** 问题集状态枚举 */
export enum CollectionStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed'
}

/** 问题集状态选项 */
export const STATUS_OPTIONS = [
  { label: '待拆解', value: CollectionStatus.PENDING },
  { label: '拆解中', value: CollectionStatus.IN_PROGRESS },
  { label: '已完成', value: CollectionStatus.COMPLETED }
];
