import { describe, expect, it } from 'vitest';
import { formatTimelineAction } from './formatTimelineAction';

describe('formatTimelineAction', () => {
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
    ).toBe('将周期从 空 改为 c1');
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
    expect(formatTimelineAction({ action_type: 'created' })).toBe('创建了此 Issue');
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
});
