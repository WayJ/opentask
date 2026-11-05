import { describe, expect, it } from 'vitest';
import { buildPublicUrl, ensureTitleField, FORM_FIELD_TYPES, formSubmitSuccessCopy } from './forms';

describe('forms helpers', () => {
  it('FORM_FIELD_TYPES includes title and custom_field', () => {
    expect(FORM_FIELD_TYPES).toContain('title');
    expect(FORM_FIELD_TYPES).toContain('custom_field');
    expect(FORM_FIELD_TYPES).toContain('assignee');
  });

  it('ensureTitleField prepends title when missing', () => {
    const out = ensureTitleField([{ key: 'description', type: 'description', label: 'D' }]);
    expect(out[0].type).toBe('title');
    expect(out).toHaveLength(2);
  });

  it('ensureTitleField keeps existing title', () => {
    const fields = [{ key: 'title', type: 'title', label: 'T', required: true }];
    expect(ensureTitleField(fields)).toEqual(fields);
  });

  it('buildPublicUrl accepts token or path', () => {
    expect(buildPublicUrl('abc', 'https://app.example')).toBe('https://app.example/f/abc');
    expect(buildPublicUrl('/f/abc', 'https://app.example')).toBe('https://app.example/f/abc');
  });
});

describe('formSubmitSuccessCopy', () => {
  it('distinguishes triage enqueued vs plain create', () => {
    expect(formSubmitSuccessCopy({ issueCode: 'OT-1', title: 'A', triageEnqueued: true })).toContain(
      '受理队列'
    );
    expect(formSubmitSuccessCopy({ issueCode: 'OT-1', title: 'A', triageEnqueued: false })).toContain(
      'OT-1'
    );
    expect(formSubmitSuccessCopy({ issueCode: 'OT-1', title: 'A', triageEnqueued: false })).not.toContain(
      '受理队列'
    );
  });
});
