import { describe, expect, it } from 'vitest';
import { mergeNotifPrefs, NOTIF_PREF_KEYS } from './notif-prefs';

describe('notif-prefs helpers', () => {
  it('mergeNotifPrefs defaults all true', () => {
    const m = mergeNotifPrefs();
    for (const k of NOTIF_PREF_KEYS) {
      expect(m[k]).toBe(true);
    }
  });

  it('mergeNotifPrefs applies partial', () => {
    const m = mergeNotifPrefs({ issue_comment: false });
    expect(m.issue_comment).toBe(false);
    expect(m.issue_assigned).toBe(true);
  });
});
