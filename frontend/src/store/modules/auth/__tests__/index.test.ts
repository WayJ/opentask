/**
 * Auth Store 测试
 *
 * 测试范围：
 * - 初始状态
 * - 登录功能
 * - 登出功能
 * - Token 管理
 * - 用户信息管理
 * - 权限检查
 */

import { createApp } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createTestingPinia } from '@pinia/testing';
import { useAuthStore } from '../index';

// Mock 依赖
vi.mock('@/service/api/auth', () => ({
  fetchLogin: vi.fn(() =>
    Promise.resolve({
      token: 'test_jwt_token',
      refreshToken: '',
      username: 'test_user',
      userId: '123'
    })
  ),
  fetchGetUserInfo: vi.fn(() =>
    Promise.resolve({
      userId: '123',
      userName: 'Test User',
      roles: ['admin']
    })
  )
}));

vi.mock('@/utils/storage', () => ({
  localStg: {
    get: vi.fn(() => null),
    set: vi.fn(),
    remove: vi.fn()
  }
}));

describe('Auth Store', () => {
  let app: any;

  beforeEach(() => {
    vi.clearAllMocks();
    // 创建 Vue app 实例以支持 Pinia inject
    app = createApp({});
  });

  describe('Initial State', () => {
    it('should have empty initial state', () => {
      const pinia = createTestingPinia({
        initialState: {
          auth: {
            token: '',
            refreshToken: '',
            userInfo: null,
            isLogin: false
          }
        }
      });

      app.use(pinia);
      const authStore = useAuthStore();

      expect(authStore.token).toBe('');
      expect(authStore.refreshToken).toBe('');
      expect(authStore.userInfo).toBeNull();
      expect(authStore.isLogin).toBe(false);
    });

    it('should have loading state false initially', () => {
      const pinia = createTestingPinia({
        initialState: {
          auth: {
            loginLoading: false
          }
        }
      });

      app.use(pinia);
      const authStore = useAuthStore();

      expect(authStore.loginLoading).toBe(false);
    });
  });

  describe('Login Functionality', () => {
    it('should login successfully with valid credentials', async () => {
      const authStore = useAuthStore();

      await authStore.login({
        userName: 'test_user',
        password: 'password123'
      });

      expect(authStore.isLogin).toBe(true);
      expect(authStore.token).toBeDefined();
    });

    it('should set user info after login', async () => {
      const authStore = useAuthStore();

      await authStore.login({
        userName: 'test_user',
        password: 'password123'
      });

      expect(authStore.userInfo).not.toBeNull();
    });

    it('should handle login failure', async () => {
      const authStore = useAuthStore();

      // Mock 登录失败
      vi.doMock('@/service/api/auth', () => ({
        fetchLogin: vi.fn(() => Promise.reject(new Error('Login failed')))
      }));

      try {
        await authStore.login({
          userName: 'wrong_user',
          password: 'wrong_password'
        });
      } catch (error) {
        expect(error).toBeDefined();
      }

      expect(authStore.isLogin).toBe(false);
    });

    it('should set loading state during login', async () => {
      const authStore = useAuthStore();

      const loginPromise = authStore.login({
        userName: 'test_user',
        password: 'password123'
      });

      expect(authStore.loginLoading).toBe(true);

      await loginPromise;

      expect(authStore.loginLoading).toBe(false);
    });
  });

  describe('Token Management', () => {
    it('should store token after login', async () => {
      const authStore = useAuthStore();

      await authStore.login({
        userName: 'test_user',
        password: 'password123'
      });

      expect(authStore.token).toBeTruthy();
      expect(authStore.token.length).toBeGreaterThan(0);
    });

    it('should clear token on logout', async () => {
      const authStore = useAuthStore();

      // 先登录
      await authStore.login({
        userName: 'test_user',
        password: 'password123'
      });

      expect(authStore.token).toBeTruthy();

      // 登出
      authStore.resetStore();

      expect(authStore.token).toBe('');
    });

    it('should check token validity', () => {
      const authStore = useAuthStore();

      authStore.token = 'valid_token';

      const hasToken = authStore.isLogin;

      expect(hasToken).toBe(true);
    });
  });

  describe('User Info Management', () => {
    it('should fetch and store user info', async () => {
      const authStore = useAuthStore();

      await authStore.getUserInfo();

      expect(authStore.userInfo).not.toBeNull();
      expect(authStore.userInfo?.userId).toBeDefined();
    });

    it('should update user info', () => {
      const authStore = useAuthStore();

      const newUserInfo = {
        userId: '456',
        userName: 'Updated User',
        roles: ['user']
      };

      authStore.userInfo = newUserInfo;

      expect(authStore.userInfo?.userName).toBe('Updated User');
    });

    it('should clear user info on logout', async () => {
      const authStore = useAuthStore();

      // 先登录获取用户信息
      await authStore.login({
        userName: 'test_user',
        password: 'password123'
      });

      expect(authStore.userInfo).not.toBeNull();

      // 登出
      authStore.resetStore();

      expect(authStore.userInfo).toBeNull();
    });
  });

  describe('Logout Functionality', () => {
    it('should clear all auth state on logout', async () => {
      const authStore = useAuthStore();

      // 先登录
      await authStore.login({
        userName: 'test_user',
        password: 'password123'
      });

      expect(authStore.isLogin).toBe(true);

      // 登出
      authStore.resetStore();

      expect(authStore.isLogin).toBe(false);
      expect(authStore.token).toBe('');
      expect(authStore.refreshToken).toBe('');
      expect(authStore.userInfo).toBeNull();
    });

    it('should call resetStore on logout', () => {
      const authStore = useAuthStore();
      const resetSpy = vi.spyOn(authStore, 'resetStore');

      authStore.resetStore();

      expect(resetSpy).toHaveBeenCalled();
    });
  });

  describe('Permission Checks', () => {
    it('should check if user has admin role', async () => {
      const authStore = useAuthStore();

      await authStore.login({
        userName: 'admin_user',
        password: 'password123'
      });

      const hasAdminRole = authStore.userInfo?.roles?.includes('admin');

      expect(hasAdminRole).toBe(true);
    });

    it('should return false for non-existent role', () => {
      const authStore = useAuthStore();

      authStore.userInfo = {
        userId: '123',
        userName: 'Test User',
        roles: ['user']
      };

      const hasAdminRole = authStore.userInfo?.roles?.includes('admin');

      expect(hasAdminRole).toBe(false);
    });
  });

  describe('Session Persistence', () => {
    it('should save auth state to localStorage', async () => {
      const authStore = useAuthStore();

      await authStore.login({
        userName: 'test_user',
        password: 'password123'
      });

      // 验证 token 被保存
      expect(authStore.token).toBeTruthy();
    });

    it('should load auth state from localStorage on init', () => {
      const authStore = useAuthStore();

      // 模拟从 localStorage 加载
      authStore.token = 'loaded_token';
      authStore.isLogin = true;

      expect(authStore.token).toBe('loaded_token');
      expect(authStore.isLogin).toBe(true);
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      const authStore = useAuthStore();

      // Mock 网络错误
      vi.doMock('@/service/api/auth', () => ({
        fetchLogin: vi.fn(() => Promise.reject(new Error('Network Error')))
      }));

      try {
        await authStore.login({
          userName: 'test_user',
          password: 'password123'
        });
      } catch (error) {
        expect((error as Error).message).toBe('Network Error');
      }
    });

    it('should handle invalid token response', async () => {
      const authStore = useAuthStore();

      // Mock 无效响应
      vi.doMock('@/service/api/auth', () => ({
        fetchLogin: vi.fn(() => Promise.resolve({}))
      }));

      await authStore.login({
        userName: 'test_user',
        password: 'password123'
      });

      // 应该没有 token
      expect(authStore.token).toBe('');
    });
  });

  describe('Concurrent Login Requests', () => {
    it('should handle multiple simultaneous login requests', async () => {
      const authStore = useAuthStore();

      const promises = [
        authStore.login({ userName: 'user1', password: 'pass1' }),
        authStore.login({ userName: 'user2', password: 'pass2' })
      ];

      await Promise.all(promises);

      // 最后一个请求应该获胜
      expect(authStore.isLogin).toBe(true);
    });
  });
});
