/** Issue Collection API 客户端 */
import { request } from '@/service/request';
import type { Api } from '@/typings/api';

export const issueCollectionApi = {
  /**
   * 获取问题集列表
   */
  getCollections: (params?: Api.IssueCollection.CollectionQueryParams) => {
    return request<Api.IssueCollection.CollectionListResponse>({
      url: '/api/issues/collections',
      method: 'GET',
      params
    });
  },

  /**
   * 获取问题集详情
   */
  getCollection: (id: string) => {
    return request<Api.IssueCollection.CollectionResponse>({
      url: `/api/issues/collections/${id}`,
      method: 'GET'
    });
  },

  /**
   * 创建问题集
   */
  createCollection: (data: Api.IssueCollection.CreateCollection) => {
    return request<Api.IssueCollection.CollectionResponse>({
      url: '/api/issues/collections',
      method: 'POST',
      data
    });
  },

  /**
   * 更新问题集
   */
  updateCollection: (id: string, data: Api.IssueCollection.UpdateCollection) => {
    return request<Api.IssueCollection.CollectionResponse>({
      url: `/api/issues/collections/${id}`,
      method: 'PUT',
      data
    });
  },

  /**
   * 删除问题集
   */
  deleteCollection: (id: string) => {
    return request({
      url: `/api/issues/collections/${id}`,
      method: 'DELETE'
    });
  },

  /**
   * 拆解问题集
   */
  parseCollection: (id: string, data: Api.IssueCollection.ParseRequest) => {
    return request<Api.IssueCollection.ParseResponse>({
      url: `/api/issues/collections/${id}/parse`,
      method: 'POST',
      data
    });
  },

  /**
   * 获取问题集统计信息
   */
  getStatistics: (id: string) => {
    return request<Api.IssueCollection.CollectionStatistics>({
      url: `/api/issues/collections/${id}/statistics`,
      method: 'GET'
    });
  }
};
