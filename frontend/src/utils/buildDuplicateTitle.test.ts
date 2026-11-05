import { describe, expect, it } from 'vitest';
import { COPY_TITLE_SUFFIX, buildDuplicateTitle } from './buildDuplicateTitle';

describe('buildDuplicateTitle', () => {
  it('appends ASCII copy suffix', () => {
    expect(COPY_TITLE_SUFFIX).toBe(' (copy)');
    expect(buildDuplicateTitle('Login')).toBe('Login (copy)');
  });

  it('override wins when non-empty', () => {
    expect(buildDuplicateTitle('Login', 'Custom')).toBe('Custom');
  });

  it('empty override falls back to suffix', () => {
    expect(buildDuplicateTitle('X', '')).toBe('X (copy)');
    expect(buildDuplicateTitle('X', '   ')).toBe('X (copy)');
  });
});
