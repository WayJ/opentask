/** OAuth2 授权 API 客户端（OpenTask 授权服务器侧） */
import { request } from '@/service/request';
import type { Api } from '@/typings/api';

/**
 * 校验授权请求并取回同意页上下文
 *
 * 后端会校验 client 状态、redirect_uri 白名单（精确匹配）、scope 允许集；
 * 非法 redirect_uri 返回 400 且**不重定向**（防开放重定向）。
 */
export function fetchOAuthAuthorizeContext(params: Api.OAuth2.AuthorizeParams) {
  return request<Api.OAuth2.AuthorizeContext>({
    url: '/api/oauth2/authorize/context',
    method: 'GET',
    params
  });
}

/**
 * 提交同意/拒绝决策
 *
 * 后端重新校验全部参数（不信任前端回传），返回应跳转的完整 URL。
 */
export function fetchOAuthAuthorizeDecision(data: Api.OAuth2.AuthorizeDecision) {
  return request<Api.OAuth2.AuthorizeDecisionResult>({
    url: '/api/oauth2/authorize/approve',
    method: 'POST',
    data
  });
}
