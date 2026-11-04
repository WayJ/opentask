import { describe, expect, it } from 'vitest';
import {
  isEmailToggleDisabled,
  mergeNotifPrefs,
  NOTIF_PREF_KEYS
} from './notif-prefs';

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

  it('mergeNotifPrefs email_enabled defaults false', () => {
    const m = mergeNotifPrefs();
    expect(m.email_enabled).toBe(false);
  });

  it('mergeNotifPrefs can enable email', () => {
    const m = mergeNotifPrefs({ email_enabled: true });
    expect(m.email_enabled).toBe(true);
  });

  it('isEmailToggleDisabled when not configured', () => {
    expect(isEmailToggleDisabled({ email_configured: false })).toBe(true);
    expect(isEmailToggleDisabled({ email_configured: true })).toBe(false);
    expect(isEmailToggleDisabled(null)).toBe(true);
  });
});
