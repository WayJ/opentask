import { request } from '../request';

/**
 * 获取分类列表
 */
export function fetchKnowledgeCategoryList(parentId?: number) {
  return request<Api.KnowledgeCategory.CategoryList>({
    url: '/api/knowledge-categories',
    method: 'get',
    params: { parentId }
  });
}

/**
 * 获取分类树
 */
export function fetchKnowledgeCategoryTree() {
  return request<Api.KnowledgeCategory.CategoryTree>({
    url: '/api/knowledge-categories/tree',
    method: 'get'
  });
}

/**
 * 获取分类详情
 */
export function fetchKnowledgeCategoryDetail(id: number) {
  return request<Api.KnowledgeCategory.Category>({
    url: `/api/knowledge-categories/${id}`,
    method: 'get'
  });
}

/**
 * 创建分类
 */
export function createKnowledgeCategory(data: Api.KnowledgeCategory.CategoryCreate) {
  return request<Api.KnowledgeCategory.Category>({
    url: '/api/knowledge-categories',
    method: 'post',
    data
  });
}

/**
 * 更新分类
 */
export function updateKnowledgeCategory(id: number, data: Api.KnowledgeCategory.CategoryUpdate) {
  return request<Api.KnowledgeCategory.Category>({
    url: `/api/knowledge-categories/${id}`,
    method: 'put',
    data
  });
}

/**
 * 删除分类
 */
export function deleteKnowledgeCategory(id: number) {
  return request<boolean>({
    url: `/api/knowledge-categories/${id}`,
    method: 'delete'
  });
}
