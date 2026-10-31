/**
 * 存储工具函数测试
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

describe('Storage Utils', () => {
  beforeEach(() => {
    // 清理测试用的 localStorage
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('localStorage operations', () => {
    it('should set and get string value', () => {
      localStorage.setItem('test_key', 'test_value');
      expect(localStorage.getItem('test_key')).toBe('test_value');
    });

    it('should handle JSON serialization', () => {
      const obj = { key: 'value', number: 123 };
      localStorage.setItem('test_obj', JSON.stringify(obj));
      const retrieved = JSON.parse(localStorage.getItem('test_obj')!);
      expect(retrieved).toEqual(obj);
    });

    it('should remove item', () => {
      localStorage.setItem('test_key', 'test_value');
      localStorage.removeItem('test_key');
      expect(localStorage.getItem('test_key')).toBeNull();
    });

    it('should clear all items', () => {
      localStorage.setItem('key1', 'value1');
      localStorage.setItem('key2', 'value2');
      localStorage.clear();
      expect(localStorage.getItem('key1')).toBeNull();
      expect(localStorage.getItem('key2')).toBeNull();
    });

    it('should handle non-existent keys', () => {
      expect(localStorage.getItem('non_existent')).toBeNull();
    });
  });

  describe('edge cases', () => {
    it('should handle empty string value', () => {
      localStorage.setItem('empty', '');
      expect(localStorage.getItem('empty')).toBe('');
    });

    it('should handle special characters in key', () => {
      const specialKey = 'key-with.special.chars';
      localStorage.setItem(specialKey, 'value');
      expect(localStorage.getItem(specialKey)).toBe('value');
    });

    it('should handle unicode values', () => {
      const unicodeValue = '测试值 🚀';
      localStorage.setItem('unicode', unicodeValue);
      expect(localStorage.getItem('unicode')).toBe(unicodeValue);
    });
  });
});
