import { describe, expect, it } from 'vitest';
import {
  issueTemplateSeedConfirmText,
  issueTemplateSourceLabel
} from './issueTemplateSourceLabel';

describe('issueTemplateSourceLabel', () => {
  it('labels seed as 内置', () => {
    expect(issueTemplateSourceLabel('seed')).toBe('内置');
  });

  it('labels custom / unknown / empty as 自定义', () => {
    expect(issueTemplateSourceLabel('custom')).toBe('自定义');
    expect(issueTemplateSourceLabel(undefined)).toBe('自定义');
    expect(issueTemplateSourceLabel(null)).toBe('自定义');
    expect(issueTemplateSourceLabel('')).toBe('自定义');
  });
});

describe('issueTemplateSeedConfirmText', () => {
  it('mentions seedKey non-overwrite', () => {
    const text = issueTemplateSeedConfirmText();
    expect(text).toContain('内置');
    expect(text).toContain('seedKey');
  });
});
