/** Access Token API 客户端 */
import { request } from '@/service/request';

export interface AccessToken {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  token_prefix: string;
  expires_at: string;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccessTokenWithToken extends AccessToken {
  token: string;
}

export interface CreateAccessTokenDto {
  name: string;
  description?: string;
}

export const accessTokenApi = {
  /** 获取所有 Access Token */
  list: () => {
    return request<AccessToken[]>({
      url: '/api/access-tokens',
      method: 'GET'
    });
  },

  /** 创建 Access Token（返回含完整 token，仅此一次） */
  create: (data: CreateAccessTokenDto) => {
    return request<AccessTokenWithToken>({
      url: '/api/access-tokens',
      method: 'POST',
      data
    });
  },

  /** 删除 Access Token */
  delete: (id: string) => {
    return request({
      url: `/api/access-tokens/${id}`,
      method: 'DELETE'
    });
  }
};
