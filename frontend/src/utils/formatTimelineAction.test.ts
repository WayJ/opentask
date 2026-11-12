import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { setLocale } from '@/locales';
import { formatTimelineAction } from './formatTimelineAction';

describe('formatTimelineAction', () => {
  beforeEach(() => setLocale('zh-CN'));
  afterEach(() => setLocale('zh-CN'));

  it('formats custom_field_changed', () => {
    expect(
      formatTimelineAction({
        action_type: 'custom_field_changed',
        action_data: { fieldKey: 'tier', from: 'a', to: 'b' }
      })
    ).toBe('将自定义字段 tier 从 a 改为 b');
  });

  it('formats cycle_changed', () => {
    expect(
      formatTimelineAction({
        action_type: 'cycle_changed',
        action_data: { from: null, to: 'c1' }
      })
    ).toBe('将冲刺从 空 改为 c1');
  });

  it('formats estimate_changed', () => {
    expect(
      formatTimelineAction({
        action_type: 'estimate_changed',
        action_data: { from: 1, to: 5 }
      })
    ).toBe('将估分从 1 改为 5');
  });

  it('formats project_changed', () => {
    expect(
      formatTimelineAction({
        action_type: 'project_changed',
        action_data: { from: 'p1', to: null }
      })
    ).toBe('将项目从 p1 改为 空');
  });

  it('keeps created', () => {
    expect(formatTimelineAction({ action_type: 'created' })).toBe('创建了此问题');
  });

  it('formats sla_paused / sla_resumed', () => {
    expect(
      formatTimelineAction({
        action_type: 'sla_paused',
        action_data: { policyName: 'FR', metric: 'first_response' }
      })
    ).toBe('暂停了首响 SLA（FR）');
    expect(
      formatTimelineAction({
        action_type: 'sla_resumed',
        action_data: { policyName: 'TIS', metric: 'time_in_status' }
      })
    ).toBe('恢复了状态 SLA（TIS）');
  });

  it('uses page.issueStatus for open, so Chinese is 待办', () => {
    setLocale('zh-CN');
    expect(
      formatTimelineAction({
        action_type: 'status_changed',
        action_data: { from: 'open', to: 'in_progress' }
      })
    ).toBe('将状态从 "待办" 改为 "进行中"');
  });

  it('switches timeline verbs and status labels with the real en-US locale', () => {
    setLocale('en-US');
    expect(formatTimelineAction({ action_type: 'created' })).toBe('Created this issue');
    expect(
      formatTimelineAction({
        action_type: 'status_changed',
        action_data: { from: 'open', to: 'in_progress' }
      })
    ).toBe('Changed status from "Open" to "In progress"');
    expect(
      formatTimelineAction({
        action_type: 'priority_changed',
        action_data: { from: 'low', to: 'high' }
      })
    ).toBe('Changed priority from "Low" to "High"');
    expect(
      formatTimelineAction({
        action_type: 'sla_paused',
        action_data: { policyName: 'FR', metric: 'first_response' }
      })
    ).toBe('Paused first-response SLA (FR)');
    expect(
      formatTimelineAction({
        action_type: 'cycle_changed',
        action_data: { from: null, to: 'c1' }
      })
    ).toBe('Changed cycle from Empty to c1');
  });
});
