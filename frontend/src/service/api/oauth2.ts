/** OAuth2 授权 API 客户端（OpenTask 授权服务器侧） */
import { request } from '@/service/request';

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


// ============================================================================
// OAuth 客户端管理（管理员）——对接既有 /api/oauth2/clients（E100）
// ============================================================================

/** 列出 OAuth client（**不含 secret 明文**，只含前缀；需 admin） */
export function fetchGetOAuthClients() {
  return request<Api.OAuth2.OAuthClient[]>({
    url: '/api/oauth2/clients',
    method: 'get'
  });
}

/** 注册 OAuth client——**client_secret 明文仅此一次返回** */
export function fetchCreateOAuthClient(data: Api.OAuth2.OAuthClientCreate) {
  return request<Api.OAuth2.OAuthClientCreated>({
    url: '/api/oauth2/clients',
    method: 'post',
    data
  });
}

/** 更新 client 元信息（name/description/redirect_uris/scopes/status） */
export function fetchUpdateOAuthClient(clientId: string, data: Api.OAuth2.OAuthClientUpdate) {
  return request<Api.OAuth2.OAuthClient>({
    url: `/api/oauth2/clients/${clientId}`,
    method: 'patch',
    data
  });
}

/** 删除 client（级联吊销其授权码与令牌） */
export function fetchDeleteOAuthClient(clientId: string) {
  return request<null>({
    url: `/api/oauth2/clients/${clientId}`,
    method: 'delete'
  });
}

/** 轮换 client secret——**新明文仅此一次返回** */
export function fetchRotateOAuthClientSecret(clientId: string) {
  return request<Api.OAuth2.OAuthClientCreated>({
    url: `/api/oauth2/clients/${clientId}/rotate-secret`,
    method: 'post'
  });
}

// ============================================================================
// 自动接入 Install Flow（E101）——对接 /api/oauth2/install/*
// 协议契约：docs/superpowers/contracts/2026-11-06-e101-oauth2-install-contract.md
// ============================================================================

/** 安装申请详情（管理员确认页用；需 admin） */
export function fetchGetOAuthInstallRequest(installId: string) {
  return request<Api.OAuth2.InstallRequestView>({
    url: `/api/oauth2/install/requests/${installId}`,
    method: 'get'
  });
}

/** 安装申请审计列表（最近 N 条；需 admin） */
export function fetchListOAuthInstallRequests(limit = 50) {
  return request<Api.OAuth2.InstallRequestView[]>({
    url: '/api/oauth2/install/requests',
    method: 'get',
    params: { limit }
  });
}

/** 批准安装 → 返回含一次性安装码的回跳 URL（需 admin） */
export function fetchApproveOAuthInstallRequest(installId: string) {
  return request<Api.OAuth2.InstallDecisionView>({
    url: `/api/oauth2/install/requests/${installId}/approve`,
    method: 'post',
    data: { approved: true }
  });
}

/** 拒绝安装（需 admin） */
export function fetchRejectOAuthInstallRequest(installId: string) {
  return request<Api.OAuth2.InstallDecisionView>({
    url: `/api/oauth2/install/requests/${installId}/reject`,
    method: 'post',
    data: {}
  });
}
