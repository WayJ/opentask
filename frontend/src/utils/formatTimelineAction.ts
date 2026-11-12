/** E41：Issue timeline action 文案（随当前 locale 读取 $t） */

import { $t } from '@/locales';

export type TimelineActionItem = {
  action_type: string;
  action_data?: Record<string, any> | null;
};

function getStatusLabel(status: string): string {
  switch (status) {
    case 'open':
      return $t('page.issueStatus.open');
    case 'in_progress':
      return $t('page.issueStatus.in_progress');
    case 'feedback':
      return $t('page.issueStatus.feedback');
    case 'resolved':
      return $t('page.issueStatus.resolved');
    case 'closed':
      return $t('page.issueStatus.closed');
    case 'rejected':
      return $t('page.issueStatus.rejected');
    default:
      return status;
  }
}

function getPriorityLabel(priority: string): string {
  switch (priority) {
    case 'low':
      return $t('page.issuePriority.low');
    case 'medium':
      return $t('page.issuePriority.medium');
    case 'high':
      return $t('page.issuePriority.high');
    case 'critical':
      return $t('page.issuePriority.critical');
    default:
      return priority;
  }
}

function relationTypeLabel(type: unknown): string {
  switch (type) {
    case 'blocks':
      return $t('page.issueDetail.relationBlocks');
    case 'is_blocked_by':
      return $t('page.issueDetail.relationBlockedBy');
    case 'relates_to':
      return $t('page.issueDetail.relationRelated');
    case 'duplicates':
      return $t('page.issueDetail.relationDuplicates');
    case 'is_duplicated_by':
      return $t('page.issueDetail.relationDuplicatedBy');
    case 'depends_on':
      return $t('page.issueDetail.relationDependsOn');
    case 'is_depended_by':
      return $t('page.issueDetail.relationDependedOnBy');
    default:
      if (type === null || type === undefined || type === '') return '';
      return String(type);
  }
}

function formatUserInfo(user: any) {
  if (!user) return $t('page.issueDetail.timelineUnassigned');
  if (typeof user === 'object') {
    return user.sso_name || user.name || user.sso_account || user.id || $t('page.issueDetail.timelineUnassigned');
  }
  return String(user);
}

function displayVal(v: unknown): string {
  if (v === null || v === undefined || v === '') return $t('page.issueDetail.timelineEmpty');
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

export function formatTimelineAction(item: TimelineActionItem): string {
  const { action_type, action_data } = item;
  const ad = action_data || {};

  switch (action_type) {
    case 'created':
      return $t('page.issueDetail.timelineCreated');
    case 'restored':
      return $t('page.issueDetail.timelineRestored');
    case 'updated':
      return $t('page.issueDetail.timelineUpdated');
    case 'commented':
      return $t('page.issueDetail.timelineCommented');
    case 'status_changed':
      return $t('page.issueDetail.timelineStatusChanged', {
        from: getStatusLabel(ad?.from || ''),
        to: getStatusLabel(ad?.to || '')
      });
    case 'assigned':
      return $t('page.issueDetail.timelineAssigneeChanged', {
        from: formatUserInfo(ad?.from),
        to: formatUserInfo(ad?.to)
      });
    case 'priority_changed':
      return $t('page.issueDetail.timelinePriorityChanged', {
        from: getPriorityLabel(ad?.from || ''),
        to: getPriorityLabel(ad?.to || '')
      });
    case 'due_date_changed':
      return $t('page.issueDetail.timelineDueDateChanged');
    case 'start_date_changed':
      return $t('page.issueDetail.timelineStartDateChanged');
    case 'relation_added':
      return $t('page.issueDetail.timelineRelationAdded', { type: relationTypeLabel(ad?.relation_type) });
    case 'relation_removed':
      return $t('page.issueDetail.timelineRelationRemoved');
    case 'attachment_added':
      return $t('page.issueDetail.timelineAttachmentAdded');
    case 'attachment_removed':
      return $t('page.issueDetail.timelineAttachmentRemoved');
    case 'label_added':
      return $t('page.issueDetail.timelineTagAdded');
    case 'label_removed':
      return $t('page.issueDetail.timelineTagRemoved');
    case 'reaction_added':
      return $t('page.issueDetail.timelineReactionAdded', { emoji: ad?.emoji || '' });
    case 'reaction_removed':
      return $t('page.issueDetail.timelineReactionRemoved', { emoji: ad?.emoji || '' });
    case 'resolved':
      return $t('page.issueDetail.timelineMarkedResolved');
    case 'closed':
      return $t('page.issueDetail.timelineClosed');
    case 'reopened':
      return $t('page.issueDetail.timelineReopened');
    case 'custom_field_changed': {
      const key = ad.fieldKey || ad.field_key || '';
      return $t('page.issueDetail.timelineCustomFieldChanged', {
        key,
        from: displayVal(ad.from),
        to: displayVal(ad.to)
      });
    }
    case 'cycle_changed':
      return $t('page.issueDetail.timelineCycleChanged', {
        from: displayVal(ad.from),
        to: displayVal(ad.to)
      });
    case 'estimate_changed':
      return $t('page.issueDetail.timelineEstimateChanged', {
        from: displayVal(ad.from),
        to: displayVal(ad.to)
      });
    case 'project_changed':
      return $t('page.issueDetail.timelineProjectChanged', {
        from: displayVal(ad.from),
        to: displayVal(ad.to)
      });
    case 'sla_paused': {
      const name = ad.policyName || ad.policyId || 'SLA';
      const metric =
        ad.metric === 'first_response'
          ? $t('page.issueDetail.timelineSlaMetricFirstResponse')
          : $t('page.issueDetail.timelineSlaMetricStatus');
      return $t('page.issueDetail.timelineSlaPaused', { metric, name });
    }
    case 'sla_resumed': {
      const name = ad.policyName || ad.policyId || 'SLA';
      const metric =
        ad.metric === 'first_response'
          ? $t('page.issueDetail.timelineSlaMetricFirstResponse')
          : $t('page.issueDetail.timelineSlaMetricStatus');
      return $t('page.issueDetail.timelineSlaResumed', { metric, name });
    }
    default:
      return action_type;
  }
}
