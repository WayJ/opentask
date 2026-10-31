/** Tag API 客户端 */
// ============================================================================
// ⚠️ Tag 功能已移除 - 知识库不再需要 tag 功能
// 此文件已废弃，API 端点已在后端禁用
// ============================================================================
import { request } from '@/service/request';
import type { Api } from '@/typings/api';

export const tagApi = {
  /**
   * 获取标签列表
   */
  getTags: (params?: { current?: number; pageSize?: number; keyword?: string }) => {
    return request<Api.Tag.TagList['data']>({
      url: '/api/tags',
      method: 'GET',
      params
    });
  },

  /**
   * 获取热门标签
   */
  getPopularTags: (limit: number = 20) => {
    return request<Api.Tag.Tag[]>({
      url: '/api/tags/popular',
      method: 'GET',
      params: { limit }
    });
  },

  /**
   * 获取标签详情
   */
  getTag: (id: number) => {
    return request<Api.Tag.Tag>({
      url: `/api/tags/${id}`,
      method: 'GET'
    });
  },

  /**
   * 创建标签
   */
  createTag: (data: Api.Tag.TagCreate) => {
    return request<Api.Tag.Tag>({
      url: '/api/tags',
      method: 'POST',
      data
    });
  },

  /**
   * 更新标签
   */
  updateTag: (id: number, data: Api.Tag.TagUpdate) => {
    return request<Api.Tag.Tag>({
      url: `/api/tags/${id}`,
      method: 'PUT',
      data
    });
  },

  /**
   * 删除标签
   */
  deleteTag: (id: number) => {
    return request<null>({
      url: `/api/tags/${id}`,
      method: 'DELETE'
    });
  }
};
