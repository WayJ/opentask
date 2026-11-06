import type { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { BACKEND_ERROR_CODE, createFlatRequest, createRequest } from '@sa/axios';
import { useAuthStore } from '@/store/modules/auth';
import { localStg } from '@/utils/storage';
import { getServiceBaseURL } from '@/utils/service';
import { workspaceRequestHeader } from '@/utils/workspace-selection';
import { $t } from '@/locales';
import { getAuthorization, handleExpiredRequest, showErrorMsg } from './shared';
import type { RequestInstanceState } from './type';

const isHttpProxy = import.meta.env.DEV && import.meta.env.VITE_HTTP_PROXY === 'Y';
const { baseURL, otherBaseURL } = getServiceBaseURL(import.meta.env, isHttpProxy);

export const request = createFlatRequest(
  {
    baseURL
  },
  {
    defaultState: {
      errMsgStack: [],
      refreshTokenPromise: null
    } as RequestInstanceState,
    transform(response: AxiosResponse<App.Service.Response<any>>) {
      return response.data.data;
    },
    async onRequest(config) {
      const Authorization = getAuthorization();
      Object.assign(config.headers, { Authorization });
      Object.assign(config.headers, workspaceRequestHeader(localStg.get('workspaceId')));

      return config;
    },
    isBackendSuccess(response) {
      // when the backend response code is 200, it means the request is success
      // to change this logic by yourself, you can modify the `VITE_SERVICE_SUCCESS_CODE` in `.env` file
      return response.data.code === Number(import.meta.env.VITE_SERVICE_SUCCESS_CODE);
    },
    async onBackendFail(response, instance) {
      const authStore = useAuthStore();
      const responseCode = String(response.data.code);

      function handleLogout() {
        authStore.resetStore();
      }

      function logoutAndCleanup() {
        handleLogout();
        window.removeEventListener('beforeunload', handleLogout);

        request.state.errMsgStack = request.state.errMsgStack.filter(msg => msg !== response.data.message);
      }

      // when the backend response code is in `logoutCodes`, it means the user will be logged out and redirected to login page
      const logoutCodes = import.meta.env.VITE_SERVICE_LOGOUT_CODES?.split(',') || [];
      if (logoutCodes.includes(responseCode)) {
        handleLogout();
        return null;
      }

      // when the backend response code is in `modalLogoutCodes`, it means the user will be logged out by displaying a modal
      const modalLogoutCodes = import.meta.env.VITE_SERVICE_MODAL_LOGOUT_CODES?.split(',') || [];
      if (modalLogoutCodes.includes(responseCode) && !request.state.errMsgStack?.includes(response.data.message)) {
        request.state.errMsgStack = [...(request.state.errMsgStack || []), response.data.message];

        // prevent the user from refreshing the page
        window.addEventListener('beforeunload', handleLogout);

        window.$dialog?.error({
          title: $t('common.error'),
          content: response.data.message,
          positiveText: $t('common.confirm'),
          maskClosable: false,
          closeOnEsc: false,
          onPositiveClick() {
            logoutAndCleanup();
          },
          onClose() {
            logoutAndCleanup();
          }
        });

        return null;
      }

      // when the backend response code is in `expiredTokenCodes`, it means the token is expired, and refresh token
      // the api `refreshToken` can not return error code in `expiredTokenCodes`, otherwise it will be a dead loop, should return `logoutCodes` or `modalLogoutCodes`
      const expiredTokenCodes = import.meta.env.VITE_SERVICE_EXPIRED_TOKEN_CODES?.split(',') || [];
      if (expiredTokenCodes.includes(responseCode)) {
        const success = await handleExpiredRequest(request.state);
        if (success) {
          const Authorization = getAuthorization();
          Object.assign(response.config.headers, { Authorization });

          return instance.request(response.config) as Promise<AxiosResponse>;
        }
      }

      return null;
    },
    // eslint-disable-next-line complexity -- 401/附件静默分支叠加，E11-S4 热修保留
    onError(error) {
      // when the request is fail, you can show error message

      // HTTP 401：token 过期的刷新重试由下方 response interceptor 统一处理，
      // onError 会在重试前先执行，这里不能登出、也不能提示（避免重试成功前误报）
      if (error.response?.status === 401) {
        // 无 token 的 401 是登录接口本身的密码错误（Phase 0 逻辑），只提示
        if (!localStg.get('token')) {
          window.$message?.error($t('page.login.common.pwdError'));
        }
        return;
      }

      // E11-S4：Issue 附件列表失败不刷屏（详情页自行兜底空列表）
      const reqUrl = String(error.config?.url || '');
      const reqMethod = String(error.config?.method || 'get').toLowerCase();
      if (reqMethod === 'get' && /\/attachments\/?$/.test(reqUrl)) {
        return;
      }

      let message = error.message;
      let backendErrorCode = '';
      const respData = error.response?.data as
        { message?: string; detail?: unknown; code?: string | number } | undefined;

      // get backend error message and code
      if (error.code === BACKEND_ERROR_CODE) {
        message = respData?.message || message;
        backendErrorCode = String(respData?.code || '');
      } else if (typeof respData?.detail === 'string' && respData.detail) {
        // FastAPI HTTPException：透出 detail（如注册弱密码「至少 8 位…」）
        message = respData.detail;
      } else if (typeof respData?.message === 'string' && respData.message) {
        message = respData.message;
      }

      // the error message is displayed in the modal
      const modalLogoutCodes = import.meta.env.VITE_SERVICE_MODAL_LOGOUT_CODES?.split(',') || [];
      if (modalLogoutCodes.includes(backendErrorCode)) {
        return;
      }

      // when the token is expired, refresh token and retry request, so no need to show error message
      const expiredTokenCodes = import.meta.env.VITE_SERVICE_EXPIRED_TOKEN_CODES?.split(',') || [];
      if (expiredTokenCodes.includes(backendErrorCode)) {
        return;
      }

      showErrorMsg(request.state, message);
    }
  }
);

/**
 * HTTP 401 刷新重试拦截器
 *
 * 已持有 token 的请求收到 401（access token 过期）时：
 * 1. 用 refreshToken 换新 token 对（并发请求共享同一次刷新）
 * 2. 刷新成功：更新 Authorization 后重放原请求（`retried` 标记防止二次重试）
 * 3. 刷新失败：resetStore 登出，拒绝原错误
 *
 * 该拦截器注册在 createFlatRequest 内置拦截器之后，
 * rejection 链中晚于 onError 执行，因此 onError 的 401 分支不做事。
 */
request.instance.interceptors.response.use(undefined, async (error: AxiosError) => {
  const config = error.config as (InternalAxiosRequestConfig & { retried?: boolean }) | undefined;

  if (error.response?.status === 401 && config && !config.retried && localStg.get('token')) {
    config.retried = true;

    const success = await handleExpiredRequest(request.state);

    if (success) {
      const Authorization = getAuthorization();
      Object.assign(config.headers, { Authorization });

      return request.instance.request(config);
    }

    const authStore = useAuthStore();
    authStore.resetStore();
  }

  return Promise.reject(error);
});

/**
 * 下载请求实例
 * 用于下载文件、文本内容等非 JSON 响应
 * 不进行 JSON 响应转换，直接返回原始数据
 */
export const downloadRequest = createRequest(
  {
    baseURL
  },
  {
    transform(response: AxiosResponse) {
      // 直接返回原始数据，不进行 JSON 转换
      return response.data;
    },
    async onRequest(config) {
      const Authorization = getAuthorization();
      Object.assign(config.headers, { Authorization });
      Object.assign(config.headers, workspaceRequestHeader(localStg.get('workspaceId')));
      return config;
    },
    isBackendSuccess(response) {
      // 对于下载请求，状态码 2xx 都表示成功
      return response.status >= 200 && response.status < 300;
    },
    async onBackendFail(_response) {
      // 下载请求的错误处理可以简单些
    },
    onError(error) {
      // 显示错误消息
      let message = error.message;
      if (error.code === BACKEND_ERROR_CODE) {
        message = error.response?.data?.message || message;
      }
      window.$message?.error(message);
    }
  }
);

export const demoRequest = createRequest(
  {
    baseURL: otherBaseURL.demo
  },
  {
    transform(response: AxiosResponse<App.Service.DemoResponse>) {
      return response.data.result;
    },
    async onRequest(config) {
      const { headers } = config;

      // set token
      const token = localStg.get('token');
      const Authorization = token ? `Bearer ${token}` : null;
      Object.assign(headers, { Authorization });

      return config;
    },
    isBackendSuccess(response) {
      // when the backend response code is "200", it means the request is success
      // you can change this logic by yourself
      return response.data.status === '200';
    },
    async onBackendFail(_response) {
      // when the backend response code is not "200", it means the request is fail
      // for example: the token is expired, refresh token and retry request
    },
    onError(error) {
      // when the request is fail, you can show error message

      let message = error.message;

      // show backend error message
      if (error.code === BACKEND_ERROR_CODE) {
        message = error.response?.data?.message || message;
      }

      window.$message?.error(message);
    }
  }
);

/**
 * SSO 平台请求实例
 * 用于调用 SSO 平台的 API（登录、获取用户信息等）
 */
export const ssoRequest = createRequest(
  {
    baseURL: otherBaseURL.sso
  },
  {
    transform(response: AxiosResponse) {
      return response.data;
    },
    async onRequest(config) {
      // SSO 需要特殊的请求头
      const { headers } = config;
      Object.assign(headers, {
        'App-Code': 'zzzz',
        'Sso-Origin': 'pc',
        'Vue-Version': '3'
      });

      return config;
    },
    isBackendSuccess(response) {
      // SSO 返回格式: { code: 200, msg: 'Success', data: {...} }
      return response.data.code === 200;
    },
    async onBackendFail(response) {
      // 处理 SSO 错误
      const message = response.data?.msg || '请求失败';
      window.$message?.error(message);
    },
    onError(error) {
      let message = error.message;
      if (error.code === BACKEND_ERROR_CODE) {
        message = error.response?.data?.msg || message;
      }
      window.$message?.error(message);
    }
  }
);
