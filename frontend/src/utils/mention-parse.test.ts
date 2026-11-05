import { describe, expect, it } from 'vitest';
import { tokenizeMentions } from './mention-parse';

describe('tokenizeMentions', () => {
  it('parses @user and issue codes', () => {
    const tokens = tokenizeMentions('hi @alice see SMK-2 and #OT-9 end');
    expect(tokens).toEqual([
      { type: 'text', value: 'hi ' },
      { type: 'user', username: 'alice' },
      { type: 'text', value: ' see ' },
      { type: 'issue', issueCode: 'SMK-2' },
      { type: 'text', value: ' and ' },
      { type: 'issue', issueCode: 'OT-9' },
      { type: 'text', value: ' end' }
    ]);
  });

  it('returns empty for empty input', () => {
    expect(tokenizeMentions('')).toEqual([]);
  });
});
