import { describe, expect, it } from 'vitest';
import {
  nextMilestoneAfterProjectMove,
  projectMoveClearedMessage
} from './nextMilestoneAfterProjectMove';

describe('nextMilestoneAfterProjectMove', () => {
  it('clears milestone when project changes', () => {
    expect(nextMilestoneAfterProjectMove('p1', 'p2', 'm1')).toBeNull();
  });

  it('keeps milestone when project unchanged', () => {
    expect(nextMilestoneAfterProjectMove('p1', 'p1', 'm1')).toBe('m1');
  });

  it('clears when project becomes null', () => {
    expect(nextMilestoneAfterProjectMove('p1', null, 'm1')).toBeNull();
  });

  it('treats undefined and null as equal empty project', () => {
    expect(nextMilestoneAfterProjectMove(undefined, null, 'm1')).toBe('m1');
  });
});

describe('projectMoveClearedMessage', () => {
  it('returns tip when milestone existed and project changed', () => {
    expect(projectMoveClearedMessage('a', 'b', true)).toBe('已清除原项目里程碑');
  });

  it('returns null when no prior milestone', () => {
    expect(projectMoveClearedMessage('a', 'b', false)).toBeNull();
  });

  it('returns null when project unchanged', () => {
    expect(projectMoveClearedMessage('a', 'a', true)).toBeNull();
  });
});
