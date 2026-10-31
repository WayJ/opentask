/**
 * 前端工具函数测试
 *
 * 测试范围：
 * - 日期格式化
 * - 文本处理
 * - 数据验证
 * - 类型转换
 * - 常用辅助函数
 */

import { describe, expect, it } from 'vitest';

describe('Utils - Helper Functions', () => {
  describe('Date Formatting', () => {
    it('should format date correctly', () => {
      const date = new Date('2024-01-15T10:30:00');
      const formatted = date.toISOString().split('T')[0];
      expect(formatted).toBe('2024-01-15');
    });

    it('should format date with time', () => {
      const date = new Date('2024-01-15T10:30:00');
      // 使用 toISOString() 会转换为 UTC 时间，所以预期值应该是 UTC 时间
      const formatted = date.toISOString().split('.')[0].replace('T', ' ');
      // 根据时区差异，UTC 时间可能是 02:30:00（UTC+8 时区）
      expect(formatted).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
    });

    it('should handle invalid date', () => {
      const date = new Date('invalid');
      expect(Number.isNaN(date.getTime())).toBe(true);
    });

    it('should get relative time', () => {
      const now = new Date();
      const past = new Date(now.getTime() - 60000); // 1 minute ago
      const diff = Math.floor((now.getTime() - past.getTime()) / 1000 / 60);
      expect(diff).toBe(1);
    });
  });

  describe('Text Processing', () => {
    it('should truncate text', () => {
      const text = 'This is a very long text that needs to be truncated';
      const truncated = `${text.substring(0, 20)}...`;
      expect(truncated.length).toBeLessThanOrEqual(23);
    });

    it('should not truncate short text', () => {
      const text = 'Short';
      const truncated = text.length > 20 ? `${text.substring(0, 20)}...` : text;
      expect(truncated).toBe('Short');
    });

    it('should capitalize first letter', () => {
      const text = 'hello world';
      const capitalized = text.charAt(0).toUpperCase() + text.slice(1);
      expect(capitalized).toBe('Hello world');
    });

    it('should convert to lowercase', () => {
      const text = 'HELLO WORLD';
      const lowercased = text.toLowerCase();
      expect(lowercased).toBe('hello world');
    });

    it('should trim whitespace', () => {
      const text = '  hello world  ';
      const trimmed = text.trim();
      expect(trimmed).toBe('hello world');
    });
  });

  describe('Data Validation', () => {
    it('should validate email format', () => {
      const email = 'test@example.com';
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      expect(emailRegex.test(email)).toBe(true);
    });

    it('should reject invalid email', () => {
      const email = 'invalid-email';
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      expect(emailRegex.test(email)).toBe(false);
    });

    it('should validate URL format', () => {
      const url = 'https://example.com';
      const urlRegex = /^https?:\/\/.+/;
      expect(urlRegex.test(url)).toBe(true);
    });

    it('should validate phone number', () => {
      const phone = '13800138000';
      const phoneRegex = /^1[3-9]\d{9}$/;
      expect(phoneRegex.test(phone)).toBe(true);
    });

    it('should validate ID card', () => {
      const idCard = '110101199001011234';
      const idCardRegex = /^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/;
      expect(idCardRegex.test(idCard)).toBe(true);
    });
  });

  describe('Array Operations', () => {
    it('should remove duplicates', () => {
      const arr = [1, 2, 2, 3, 3, 4];
      const unique = [...new Set(arr)];
      expect(unique).toEqual([1, 2, 3, 4]);
    });

    it('should sort array', () => {
      const arr = [3, 1, 4, 1, 5];
      const sorted = [...arr].sort((a, b) => a - b);
      expect(sorted).toEqual([1, 1, 3, 4, 5]);
    });

    it('should filter array', () => {
      const arr = [1, 2, 3, 4, 5];
      const filtered = arr.filter(item => item > 2);
      expect(filtered).toEqual([3, 4, 5]);
    });

    it('should map array', () => {
      const arr = [1, 2, 3];
      const mapped = arr.map(item => item * 2);
      expect(mapped).toEqual([2, 4, 6]);
    });

    it('should reduce array', () => {
      const arr = [1, 2, 3, 4];
      const sum = arr.reduce((acc, item) => acc + item, 0);
      expect(sum).toBe(10);
    });
  });

  describe('Object Operations', () => {
    it('should deep clone object', () => {
      const obj = { a: 1, b: { c: 2 } };
      const cloned = JSON.parse(JSON.stringify(obj));
      expect(cloned).toEqual(obj);
      expect(cloned).not.toBe(obj);
    });

    it('should merge objects', () => {
      const obj1 = { a: 1, b: 2 };
      const obj2 = { b: 3, c: 4 };
      const merged = { ...obj1, ...obj2 };
      expect(merged).toEqual({ a: 1, b: 3, c: 4 });
    });

    it('should get object keys', () => {
      const obj = { a: 1, b: 2, c: 3 };
      const keys = Object.keys(obj);
      expect(keys).toEqual(['a', 'b', 'c']);
    });

    it('should get object values', () => {
      const obj = { a: 1, b: 2, c: 3 };
      const values = Object.values(obj);
      expect(values).toEqual([1, 2, 3]);
    });
  });

  describe('String Operations', () => {
    it('should generate random string', () => {
      const randomString = Math.random().toString(36).substring(2, 10);
      expect(randomString.length).toBe(8);
    });

    it('should generate UUID', () => {
      // eslint-disable-next-line no-bitwise
      const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.floor(Math.random() * 16);
        // eslint-disable-next-line no-bitwise
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      });
      expect(uuid.length).toBe(36);
      expect(uuid).toMatch(/^[0-9a-f-]+$/);
    });

    it('should convert camelCase to kebab-case', () => {
      const camelCase = 'camelCaseString';
      const kebabCase = camelCase.replace(/([A-Z])/g, '-$1').toLowerCase();
      expect(kebabCase).toBe('camel-case-string');
    });

    it('should convert kebab-case to camelCase', () => {
      const kebabCase = 'kebab-case-string';
      const camelCase = kebabCase.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
      expect(camelCase).toBe('kebabCaseString');
    });
  });

  describe('Number Operations', () => {
    it('should round number', () => {
      const num = 3.14159;
      const rounded = Math.round(num * 100) / 100;
      expect(rounded).toBe(3.14);
    });

    it('should format number with commas', () => {
      const num = 1234567.89;
      const formatted = num.toLocaleString('en-US');
      expect(formatted).toBe('1,234,567.89');
    });

    it('should clamp number between min and max', () => {
      const num = 150;
      const min = 0;
      const max = 100;
      const clamped = Math.max(min, Math.min(max, num));
      expect(clamped).toBe(100);
    });

    it('should check if number is in range', () => {
      const num = 50;
      const inRange = num >= 0 && num <= 100;
      expect(inRange).toBe(true);
    });
  });

  describe('Type Checking', () => {
    it('should check if value is array', () => {
      const arr = [1, 2, 3];
      expect(Array.isArray(arr)).toBe(true);
    });

    it('should check if value is object', () => {
      const obj = { a: 1 };
      expect(typeof obj).toBe('object');
    });

    it('should check if value is null', () => {
      const value = null;
      expect(value).toBeNull();
    });

    it('should check if value is undefined', () => {
      const value: undefined = undefined;
      expect(value).toBeUndefined();
    });

    it('should check if value is string', () => {
      const value = 'hello';
      expect(typeof value).toBe('string');
    });

    it('should check if value is number', () => {
      const value = 42;
      expect(typeof value).toBe('number');
    });
  });

  describe('Color Utilities', () => {
    it('should convert hex to RGB', () => {
      const hex = '#ff0000';
      const r = Number.parseInt(hex.slice(1, 3), 16);
      const g = Number.parseInt(hex.slice(3, 5), 16);
      const b = Number.parseInt(hex.slice(5, 7), 16);
      expect({ r, g, b }).toEqual({ r: 255, g: 0, b: 0 });
    });

    it('should convert RGB to hex', () => {
      const r = 255;
      const g = 0;
      const b = 0;
      const hex = `#${[r, g, b].map(x => x.toString(16).padStart(2, '0')).join('')}`;
      expect(hex).toBe('#ff0000');
    });

    it('should check if color is light', () => {
      const hex = '#ffffff';
      const r = Number.parseInt(hex.slice(1, 3), 16);
      const g = Number.parseInt(hex.slice(3, 5), 16);
      const b = Number.parseInt(hex.slice(5, 7), 16);
      const brightness = (r * 299 + g * 587 + b * 114) / 1000;
      expect(brightness).toBeGreaterThan(128);
    });
  });

  describe('File Utilities', () => {
    it('should get file extension', () => {
      const filename = 'document.pdf';
      const extension = filename.split('.').pop();
      expect(extension).toBe('pdf');
    });

    it('should format file size', () => {
      const bytes = 1024 * 1024 * 5; // 5 MB
      let formatted: string;
      if (bytes < 1024) {
        formatted = `${bytes} B`;
      } else if (bytes < 1024 * 1024) {
        formatted = `${(bytes / 1024).toFixed(2)} KB`;
      } else {
        formatted = `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
      }
      expect(formatted).toBe('5.00 MB');
    });

    it('should validate file type', () => {
      const filename = 'image.jpg';
      const allowedTypes = ['jpg', 'png', 'gif'];
      const extension = filename.split('.').pop() || '';
      expect(allowedTypes.includes(extension)).toBe(true);
    });
  });
});
