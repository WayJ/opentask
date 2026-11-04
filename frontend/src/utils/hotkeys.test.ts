import { describe, expect, it } from 'vitest';
import { ignoreWhenEditable, isModK } from './hotkeys';

describe('isModK', () => {
  it('matches Meta+K', () => {
    expect(isModK({ key: 'k', metaKey: true, ctrlKey: false })).toBe(true);
    expect(isModK({ key: 'K', metaKey: true, ctrlKey: false })).toBe(true);
  });

  it('matches Ctrl+K', () => {
    expect(isModK({ key: 'k', metaKey: false, ctrlKey: true })).toBe(true);
  });

  it('rejects K without modifier and other keys', () => {
    expect(isModK({ key: 'k', metaKey: false, ctrlKey: false })).toBe(false);
    expect(isModK({ key: 'Escape', metaKey: true, ctrlKey: false })).toBe(false);
  });
});

describe('ignoreWhenEditable', () => {
  it('is true for input/textarea/select', () => {
    expect(ignoreWhenEditable(document.createElement('input'))).toBe(true);
    expect(ignoreWhenEditable(document.createElement('textarea'))).toBe(true);
    expect(ignoreWhenEditable(document.createElement('select'))).toBe(true);
  });

  it('is true for contenteditable ancestor', () => {
    const wrap = document.createElement('div');
    wrap.setAttribute('contenteditable', 'true');
    const child = document.createElement('span');
    wrap.appendChild(child);
    document.body.appendChild(wrap);
    expect(ignoreWhenEditable(child)).toBe(true);
    wrap.remove();
  });

  it('is false for plain div', () => {
    expect(ignoreWhenEditable(document.createElement('div'))).toBe(false);
    expect(ignoreWhenEditable(null)).toBe(false);
  });
});
