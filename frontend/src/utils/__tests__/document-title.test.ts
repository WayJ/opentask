import { describe, expect, it } from 'vitest';
import { formatDocumentTitle } from '../document-title';

describe('formatDocumentTitle', () => {
  it('keeps OpenTask when the page title is empty or already the product name', () => {
    expect(formatDocumentTitle('')).toBe('OpenTask');
    expect(formatDocumentTitle('OpenTask')).toBe('OpenTask');
    expect(formatDocumentTitle(null)).toBe('OpenTask');
  });

  it('suffixes the product name for a page title', () => {
    expect(formatDocumentTitle('我的问题')).toBe('我的问题 - OpenTask');
    expect(formatDocumentTitle('My issues')).toBe('My issues - OpenTask');
  });
});
