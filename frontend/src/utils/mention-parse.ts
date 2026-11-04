/** E20：与后端 _MENTION_RE 对齐的 @token；Issue code KEY-123 / #KEY-123 */
export const USER_MENTION_RE = /@([A-Za-z0-9_.-]{1,64})/g;
export const ISSUE_CODE_RE = /#?([A-Z][A-Z0-9]*-\d+)/g;

export type MentionToken =
  | { type: 'text'; value: string }
  | { type: 'user'; username: string }
  | { type: 'issue'; issueCode: string };

/** 将纯文本切成 text / @user / Issue code token（不重叠，从左到右）。 */
export function tokenizeMentions(input: string): MentionToken[] {
  if (!input) return [];
  const combined = /(@[A-Za-z0-9_.-]{1,64})|(#?[A-Z][A-Z0-9]*-\d+)/g;
  const out: MentionToken[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = combined.exec(input)) !== null) {
    if (m.index > last) {
      out.push({ type: 'text', value: input.slice(last, m.index) });
    }
    const raw = m[0];
    if (raw.startsWith('@')) {
      out.push({ type: 'user', username: raw.slice(1) });
    } else {
      out.push({ type: 'issue', issueCode: raw.replace(/^#/, '') });
    }
    last = m.index + raw.length;
  }
  if (last < input.length) out.push({ type: 'text', value: input.slice(last) });
  return out;
}
