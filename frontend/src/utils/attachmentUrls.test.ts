import { describe, expect, it } from 'vitest';
import { attachmentAccessDeniedMessage, toBrowserAttachmentUrl } from './attachmentUrls';

describe('attachmentUrls', () => {
  it('prefixes /opentask for relative API paths', () => {
    expect(toBrowserAttachmentUrl('/api/attachments/signed/tok')).toBe(
      '/opentask/api/attachments/signed/tok'
    );
  });

  it('passes through absolute URLs', () => {
    expect(toBrowserAttachmentUrl('https://cdn.example/x')).toBe('https://cdn.example/x');
  });

  it('does not double-prefix /opentask', () => {
    expect(toBrowserAttachmentUrl('/opentask/api/attachments/signed/t')).toBe(
      '/opentask/api/attachments/signed/t'
    );
  });

  it('friendly 401/404 copy', () => {
    expect(attachmentAccessDeniedMessage(401)).toMatch(/登录|未授权|认证/);
    expect(attachmentAccessDeniedMessage(404)).toMatch(/不存在|无权限|找不到/);
  });
});
