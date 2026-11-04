import { describe, expect, it } from 'vitest';
import { REG_PWD } from './reg';

describe('REG_PWD (register / form password policy)', () => {
  it('rejects passwords shorter than 8 characters', () => {
    expect(REG_PWD.test('Ab12')).toBe(false);
    expect(REG_PWD.test('Abc12')).toBe(false);
    expect(REG_PWD.test('Abc1234')).toBe(false);
  });

  it('rejects 8+ passwords missing a letter or a digit', () => {
    expect(REG_PWD.test('abcdefgh')).toBe(false);
    expect(REG_PWD.test('12345678')).toBe(false);
  });

  it('accepts passwords with at least 8 chars including letter and digit', () => {
    expect(REG_PWD.test('Abcdef12')).toBe(true);
    expect(REG_PWD.test('Passw0rd!')).toBe(true);
    expect(REG_PWD.test('SmokeTest123!')).toBe(true);
  });
});
