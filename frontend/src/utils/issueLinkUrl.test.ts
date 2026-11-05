import { describe, expect, it } from 'vitest';
import { hostnameFromUrl, isHttpUrl } from './issueLinkUrl';

describe('isHttpUrl', () => {
  it('accepts http and https', () => {
    expect(isHttpUrl('https://figma.com/file/x')).toBe(true);
    expect(isHttpUrl('http://example.com')).toBe(true);
    expect(isHttpUrl('  https://a.io/b  ')).toBe(true);
  });

  it('rejects non-http schemes and relative', () => {
    expect(isHttpUrl('')).toBe(false);
    expect(isHttpUrl('javascript:alert(1)')).toBe(false);
    expect(isHttpUrl('/relative')).toBe(false);
    expect(isHttpUrl('ftp://x.com')).toBe(false);
    expect(isHttpUrl('https://')).toBe(false);
  });
});

describe('hostnameFromUrl', () => {
  it('returns hostname', () => {
    expect(hostnameFromUrl('https://figma.com/file/x')).toBe('figma.com');
    expect(hostnameFromUrl('http://docs.example.com:8080/a')).toBe('docs.example.com');
  });

  it('falls back to raw when unparseable', () => {
    expect(hostnameFromUrl('not a url')).toBe('not a url');
  });
});
