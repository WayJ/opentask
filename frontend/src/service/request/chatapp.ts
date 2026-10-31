/**
 * ChatApp 专用请求实例
 *
 * ChatApp 是独立的 Node.js 后端，运行在 3001 端口
 * 需要携带 OpenTask 的 token 进行认证
 */

import type { AxiosResponse } from 'axios';
import { BACKEND_ERROR_CODE, createRequest } from '@sa/axios';
import { localStg } from '@/utils/storage';

const CHATAPP_BASE_URL = import.meta.env.VITE_CHATAPP_URL || 'http://localhost:3001';

/**
 * 获取 OpenTask 的认证 token
 * 用于传递给 ChatApp 后端
 */
function getOpenTaskAuthorization() {
  const token = localStg.get('token');
  return token ? `Bearer ${token}` : null;
}

/**
 * ChatApp 请求实例
 * 用于调用 ChatApp 后端 API
 */
export const chatappRequest = createRequest(
  {
    baseURL: CHATAPP_BASE_URL
  },
  {
    transform(response: AxiosResponse<App.Service.Response<any>>) {
      return response.data.data;
    },
    async onRequest(config) {
      // 携带 OpenTask 的 token
      const Authorization = getOpenTaskAuthorization();
      if (Authorization) {
        Object.assign(config.headers, { Authorization });
      }
      return config;
    },
    isBackendSuccess(response) {
      // ChatApp 返回格式与 OpenTask 一致
      return response.data.code === 200;
    },
    async onBackendFail(response) {
      // 处理 ChatApp 错误
      const message = response.data?.message || 'Request failed';
      window.$message?.error(message);
    },
    onError(error) {
      let message = error.message;

      if (error.code === BACKEND_ERROR_CODE) {
        message = error.response?.data?.message || message;
      }

      window.$message?.error(message);
    }
  }
);

/**
 * ChatApp 下载请求实例
 * 用于下载文件等非 JSON 响应
 */
export const chatappDownloadRequest = createRequest(
  {
    baseURL: CHATAPP_BASE_URL
  },
  {
    transform(response: AxiosResponse) {
      return response.data;
    },
    async onRequest(config) {
      const Authorization = getOpenTaskAuthorization();
      if (Authorization) {
        Object.assign(config.headers, { Authorization });
      }
      return config;
    },
    isBackendSuccess(response) {
      return response.status >= 200 && response.status < 300;
    },
    async onBackendFail(_response) {
      // 下载请求的错误处理
    },
    onError(error) {
      let message = error.message;
      if (error.code === BACKEND_ERROR_CODE) {
        message = error.response?.data?.message || message;
      }
      window.$message?.error(message);
    }
  }
);
