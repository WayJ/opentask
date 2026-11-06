import { describe, expect, it } from 'vitest';
import {
  attachmentAccessDeniedMessage,
  browserServiceUrl,
  commentAttachmentToDocument,
  flattenCommentAttachments,
  toBrowserAttachmentUrl
} from './attachmentUrls';

const devProxy = { DEV: true, VITE_HTTP_PROXY: 'Y', VITE_SERVICE_BASE_URL: 'http://localhost:7377' };
const prodRoot = { DEV: false, VITE_HTTP_PROXY: 'N', VITE_SERVICE_BASE_URL: '/' };

describe('attachmentUrls', () => {
  it('prefixes /opentask for the local vite proxy', () => {
    expect(toBrowserAttachmentUrl('/api/attachments/signed/tok', devProxy)).toBe(
      '/opentask/api/attachments/signed/tok'
    );
  });

  it('keeps /api when the production service base is /', () => {
    expect(toBrowserAttachmentUrl('/api/attachments/signed/tok', prodRoot)).toBe('/api/attachments/signed/tok');
  });

  it('does not turn a root service base into a protocol-relative public URL', () => {
    expect(browserServiceUrl('/api/public/forms/tok', '/')).toBe('/api/public/forms/tok');
    expect(browserServiceUrl('/api/public/forms/tok', '')).toBe('/api/public/forms/tok');
    expect(browserServiceUrl('/api/public/forms/tok', '/opentask/')).toBe('/opentask/api/public/forms/tok');
    expect(browserServiceUrl('/api/public/forms/tok', 'http://localhost:7377')).toBe(
      'http://localhost:7377/api/public/forms/tok'
    );
  });

  it('passes through absolute URLs', () => {
    expect(toBrowserAttachmentUrl('https://cdn.example/x', prodRoot)).toBe('https://cdn.example/x');
  });

  it('does not double-prefix /opentask', () => {
    expect(toBrowserAttachmentUrl('/opentask/api/attachments/signed/t', devProxy)).toBe(
      '/opentask/api/attachments/signed/t'
    );
  });

  it('friendly 401/404 copy', () => {
    expect(attachmentAccessDeniedMessage(401)).toMatch(/登录|未授权|认证/);
    expect(attachmentAccessDeniedMessage(404)).toMatch(/不存在|无权限|找不到/);
  });
});

describe('flattenCommentAttachments (E69)', () => {
  it('flattens nested comment attachment summaries', () => {
    const flat = flattenCommentAttachments([
      {
        id: 'c1',
        attachments: [{ id: 'a1', file_name: 'x.png', file_size: 10, file_type: 'image/png' }]
      },
      { id: 'c2', attachments: [] },
      {
        id: 'c3',
        attachments: [
          { id: 'a2', file_name: 'y.txt', file_size: 3, file_type: 'text/plain' },
          { id: 'a3', file_name: 'z.pdf', file_size: 9, file_type: 'application/pdf' }
        ]
      }
    ]);
    expect(flat).toEqual([
      { commentId: 'c1', id: 'a1', file_name: 'x.png', file_size: 10, file_type: 'image/png' },
      { commentId: 'c3', id: 'a2', file_name: 'y.txt', file_size: 3, file_type: 'text/plain' },
      { commentId: 'c3', id: 'a3', file_name: 'z.pdf', file_size: 9, file_type: 'application/pdf' }
    ]);
  });

  it('maps summary to document-shaped row', () => {
    const doc = commentAttachmentToDocument(
      { id: 'a1', file_name: 'n.txt', file_size: 1, file_type: 'text/plain' },
      'c9'
    );
    expect(doc.entity_type).toBe('issue_comment');
    expect(doc.entity_id).toBe('c9');
    expect(doc.id).toBe('a1');
  });
});
