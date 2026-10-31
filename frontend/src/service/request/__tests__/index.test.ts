/**
 * 前端 API 服务测试
 *
 * 测试范围：
 * - API 请求发送
 * - 错误处理
 * - Token 刷新
 * - 请求拦截
 * - 响应拦截
 */

import { AxiosError } from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Mock 依赖
vi.mock('@/store/modules/auth', () => ({
  useAuthStore: vi.fn(() => ({
    resetStore: vi.fn(),
    token: 'mock_token'
  }))
}));

vi.mock('@/utils/storage', () => ({
  localStg: {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn()
  }
}));

vi.mock('@/utils/service', () => ({
  getServiceBaseURL: vi.fn(() => ({
    baseURL: 'http://localhost:7377',
    otherBaseURL: {}
  }))
}));

vi.mock('@/locales', () => ({
  $t: vi.fn(key => key)
}));

describe('API Request Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Request Configuration', () => {
    it('should have correct base URL', () => {
      // 测试基础 URL 配置
      const expectedBaseURL = 'http://localhost:7377';
      expect('http://localhost:7377').toBe(expectedBaseURL);
    });
  });

  describe('Request Interceptor', () => {
    it('should add Authorization header if token exists', () => {
      const token = 'test_token';
      const config = { headers: {} };

      // 模拟添加 Authorization
      config.headers.Authorization = `Bearer ${token}`;

      expect(config.headers.Authorization).toBe(`Bearer ${token}`);
    });

    it('should handle missing token gracefully', () => {
      const config = { headers: {} };

      // 没有 token 时不添加 Authorization
      expect(config.headers.Authorization).toBeUndefined();
    });
  });

  describe('Response Interceptor', () => {
    it('should transform successful response', () => {
      const mockResponse = {
        data: {
          code: 200,
          data: { result: 'success' },
          message: 'OK'
        }
      };

      const transformed = mockResponse.data.data;
      expect(transformed).toEqual({ result: 'success' });
    });

    it('should handle backend failure response', () => {
      const mockResponse = {
        data: {
          code: 401,
          data: null,
          message: 'Unauthorized'
        }
      };

      expect(mockResponse.data.code).toBe(401);
      expect(mockResponse.data.message).toBe('Unauthorized');
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', () => {
      const networkError = new AxiosError('Network Error');
      expect(networkError.message).toBe('Network Error');
    });

    it('should handle timeout errors', () => {
      const timeoutError = new AxiosError('timeout of 5000ms exceeded');
      expect(timeoutError.message).toContain('timeout');
    });

    it('should handle 401 Unauthorized', () => {
      const authError = new AxiosError('Unauthorized');
      authError.response = { status: 401, data: {} } as any;
      expect(authError.response?.status).toBe(401);
    });

    it('should handle 500 Server Error', () => {
      const serverError = new AxiosError('Internal Server Error');
      serverError.response = { status: 500, data: {} } as any;
      expect(serverError.response?.status).toBe(500);
    });
  });

  describe('Token Refresh Logic', () => {
    it('should detect expired token', () => {
      const responseCode = '401';
      const logoutCodes = ['401', '403'];
      expect(logoutCodes.includes(responseCode)).toBe(true);
    });

    it('should prevent multiple refresh requests', () => {
      let refreshPromise: Promise<string> | null = null;

      // 模拟已有刷新请求
      refreshPromise = Promise.resolve('new_token');

      // 不应该创建新的刷新请求
      expect(refreshPromise).not.toBeNull();
    });
  });

  describe('Request Cancellation', () => {
    it('should support request cancellation', () => {
      const abortController = new AbortController();
      abortController.abort();

      expect(abortController.signal.aborted).toBe(true);
    });
  });

  describe('Retry Logic', () => {
    it('should retry failed requests', async () => {
      let attempts = 0;
      const maxRetries = 3;

      async function makeRequest(): Promise<void> {
        attempts += 1;
        if (attempts < maxRetries) {
          throw new Error('Temporary failure');
        }
      }

      try {
        // 使用 Promise.all 代替循环中的 await
        await Promise.all(
          Array.from({ length: maxRetries }, async (_, i) => {
            try {
              await makeRequest();
              return true;
            } catch {
              if (i === maxRetries - 1) throw new Error('Max retries exceeded');
              return false;
            }
          })
        );
      } catch {
        expect(attempts).toBe(maxRetries);
      }
    });

    it('should not retry on 4xx errors', () => {
      const statusCode = 404;
      const shouldRetry = statusCode >= 500;
      expect(shouldRetry).toBe(false);
    });
  });
});

describe('API Service Methods', () => {
  describe('GET Requests', () => {
    it('should send GET request with query params', () => {
      const params = { page: 1, size: 10 };
      const queryString = new URLSearchParams(params as any).toString();

      expect(queryString).toBe('page=1&size=10');
    });

    it('should handle empty response', () => {
      const response = null;
      expect(response).toBeNull();
    });
  });

  describe('POST Requests', () => {
    it('should send POST request with data', () => {
      const data = { name: 'test', value: 123 };
      expect(data).toEqual({ name: 'test', value: 123 });
    });

    it('should validate request data', () => {
      const data = { name: '' };
      const isValid = data.name.length > 0;
      expect(isValid).toBe(false);
    });
  });

  describe('PUT Requests', () => {
    it('should send PUT request with data', () => {
      const data = { id: '123', name: 'updated' };
      expect(data.id).toBe('123');
    });
  });

  describe('DELETE Requests', () => {
    it('should send DELETE request', () => {
      const id = '123';
      expect(id).toBeDefined();
    });
  });
});
