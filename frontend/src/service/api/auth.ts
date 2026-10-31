import { axios } from '@sa/axios';
import { getServiceBaseURL } from '@/utils/service';
import { request } from '../request';

const isHttpProxy = import.meta.env.DEV && import.meta.env.VITE_HTTP_PROXY === 'Y';
const { baseURL } = getServiceBaseURL(import.meta.env, isHttpProxy);

/**
 * 刷新 token 专用裸 axios 实例
 *
 * 不走全局 request 实例：refresh 自身失败返回 HTTP 401，
 * 若走全局拦截器会在 401 处理中再次触发刷新，形成递归。
 */
const refreshInstance = axios.create({ baseURL });

/**
 * Login - 调用 opentask 登录接口（密码明文传输，依赖 HTTPS）
 *
 * @param userName User name
 * @param password Password
 */
export function fetchLogin(userName: string, password: string) {
  return request<Api.Auth.LoginToken>({
    url: '/api/auth/login',
    method: 'post',
    data: {
      userName,
      password
    }
  });
}

/** Get user info */
export function fetchGetUserInfo() {
  return request<Api.Auth.UserInfo>({ url: '/api/auth/getUserInfo' });
}

/** Get current user info */
export function fetchGetCurrentUser() {
  return request<Api.SystemManage.CurrentUser>({ url: '/api/users/me' });
}

/**
 * Change password（首次登录强制改密 / 主动修改）
 *
 * 成功返回新的正常 token 对；旧密码错误 401，弱密码 422。
 *
 * @param oldPassword Old password
 * @param newPassword New password
 */
export function fetchChangePassword(data: { oldPassword: string; newPassword: string }) {
  return request<Api.Auth.LoginToken>({
    url: '/api/auth/change-password',
    method: 'post',
    data
  });
}

/**
 * Refresh token（轮换式，返回新 token 对；失败抛 HTTP 401）
 *
 * @param refreshToken Refresh token
 */
export async function fetchRefreshToken(refreshToken: string) {
  const response = await refreshInstance.post<App.Service.Response<Api.Auth.LoginToken>>('/api/auth/refreshToken', {
    refreshToken
  });

  return response.data.data;
}

/**
 * return custom backend error
 *
 * @param code error code
 * @param msg error message
 */
export function fetchCustomBackendError(code: string, msg: string) {
  return request({ url: '/api/auth/error', params: { code, msg } });
}

/** 钉钉登录配置（免鉴权；enabled=false 时登录页隐藏钉钉入口） */
export function fetchDingtalkConfig() {
  return request<{ enabled: boolean; appKey: string | null }>({
    url: '/api/auth/dingtalk/config',
    method: 'get'
  });
}

/** 钉钉免登回调（authCode → 本地账号定位/自动建号 → token 对） */
export function fetchDingtalkCallback(authCode: string) {
  return request<Api.Auth.LoginToken>({
    url: '/api/auth/dingtalk/callback',
    method: 'post',
    data: { authCode }
  });
}
