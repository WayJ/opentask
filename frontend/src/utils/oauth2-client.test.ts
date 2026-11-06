import { describe, expect, it } from 'vitest';
import {
  KNOWN_OAUTH_SCOPES,
  installStatusLabel,
  isKnownScope,
  normalizeScopeList,
  parseRedirectUriList,
  scopeEndpoint,
  scopeLabel,
  validateRedirectUri
} from './oauth2-client';

describe('parseRedirectUriList', () => {
  it('多行输入切分为列表并去除空白项', () => {
    expect(parseRedirectUriList('https://a.example.com/cb\n\nhttps://b.example.com/cb\n')).toEqual([
      'https://a.example.com/cb',
      'https://b.example.com/cb'
    ]);
  });

  it('逗号分隔同样支持', () => {
    expect(parseRedirectUriList('https://a.example.com/cb, https://b.example.com/cb')).toEqual([
      'https://a.example.com/cb',
      'https://b.example.com/cb'
    ]);
  });

  it('重复项去重且保持首次出现顺序', () => {
    expect(
      parseRedirectUriList('https://a.example.com/cb\nhttps://a.example.com/cb\nhttps://b.example.com/cb')
    ).toEqual(['https://a.example.com/cb', 'https://b.example.com/cb']);
  });

  it('空输入返回空数组', () => {
    expect(parseRedirectUriList('')).toEqual([]);
    expect(parseRedirectUriList('  \n  ')).toEqual([]);
  });
});

describe('validateRedirectUri', () => {
  it('绝对 https URL 通过', () => {
    expect(validateRedirectUri('https://xiaolan.example.com/enterprise/api/v1/app-oauth/opentask/callback').valid).toBe(
      true
    );
  });

  it('绝对 http URL 通过（本地开发）', () => {
    expect(validateRedirectUri('http://localhost:9527/oauth2-demo-callback').valid).toBe(true);
  });

  it('相对路径被拒', () => {
    expect(validateRedirectUri('/relative/callback').valid).toBe(false);
  });

  it('非 http(s) 协议被拒', () => {
    expect(validateRedirectUri('ftp://a.example.com/cb').valid).toBe(false);
    const jsScheme = ['java', 'script:alert(1)'].join('');
    expect(validateRedirectUri(jsScheme).valid).toBe(false);
  });

  it('含空白被拒', () => {
    expect(validateRedirectUri('https://a.example.com/cb ').valid).toBe(false);
  });

  it('空串被拒', () => {
    expect(validateRedirectUri('  ').valid).toBe(false);
  });
});

describe('normalizeScopeList', () => {
  it('字符串按空格/逗号切分并去重', () => {
    expect(normalizeScopeList('read:tasks read:projects, profile read:tasks')).toEqual([
      'read:tasks',
      'read:projects',
      'profile'
    ]);
  });

  it('数组输入原样去重', () => {
    expect(normalizeScopeList(['read:tasks', 'read:tasks', 'profile'])).toEqual(['read:tasks', 'profile']);
  });

  it('空输入返回空数组', () => {
    expect(normalizeScopeList('')).toEqual([]);
    expect(normalizeScopeList([])).toEqual([]);
  });
});

describe('KNOWN_OAUTH_SCOPES', () => {
  it('目录与后端 provider 一致（4 个只读 scope）', () => {
    expect(KNOWN_OAUTH_SCOPES.map(item => item.scope).sort()).toEqual([
      'profile',
      'read:projects',
      'read:requirements',
      'read:tasks'
    ]);
  });

  it('每个条目都有中文说明与数据面端点', () => {
    for (const item of KNOWN_OAUTH_SCOPES) {
      expect(item.label.length).toBeGreaterThan(0);
      expect(item.endpoint.startsWith('GET /oauth2/api/') || item.endpoint.startsWith('GET /oauth2/userinfo')).toBe(
        true
      );
    }
  });
});

describe('scopeLabel / scopeEndpoint / isKnownScope', () => {
  it('已知 scope 返回中文说明与端点', () => {
    expect(scopeLabel('read:tasks')).toBe('读取任务列表与详情');
    expect(scopeEndpoint('profile')).toBe('GET /oauth2/userinfo');
    expect(isKnownScope('read:tasks')).toBe(true);
  });

  it('未知 scope 回退展示原值（不静默吞掉）', () => {
    const unknown = 'read:comments';
    expect(scopeLabel(unknown)).toBe(unknown);
    expect(scopeEndpoint(unknown)).toBe('');
    expect(isKnownScope(unknown)).toBe(false);
  });
});

describe('installStatusLabel', () => {
  it('五种状态均有中文文案', () => {
    expect(installStatusLabel('PENDING')).toBe('待确认');
    expect(installStatusLabel('APPROVED')).toContain('已批准');
    expect(installStatusLabel('REJECTED')).toBe('已拒绝');
    expect(installStatusLabel('EXPIRED')).toBe('已过期');
    expect(installStatusLabel('CONSUMED')).toContain('已完成');
  });

  it('未知状态回退原值', () => {
    expect(installStatusLabel('WEIRD')).toBe('WEIRD');
  });
});
