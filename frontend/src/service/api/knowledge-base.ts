import { request } from '../request';

/**
 * 获取知识库列表
 */
export function fetchKnowledgeBaseList(params?: Api.KnowledgeBase.KnowledgeBaseSearchParams) {
  return request<Api.KnowledgeBase.KnowledgeBaseList>({
    url: '/api/knowledge-bases',
    method: 'get',
    params
  });
}

/**
 * 获取知识库详情
 */
export function fetchKnowledgeBaseDetail(id: string) {
  return request<Api.KnowledgeBase.KnowledgeBase>({
    url: `/api/knowledge-bases/${id}`,
    method: 'get'
  });
}

/**
 * 创建知识库
 */
export function createKnowledgeBase(data: Api.KnowledgeBase.KnowledgeBaseCreate) {
  return request<Api.KnowledgeBase.KnowledgeBase>({
    url: '/api/knowledge-bases',
    method: 'post',
    data
  });
}

/**
 * 更新知识库
 */
export function updateKnowledgeBase(id: string, data: Api.KnowledgeBase.KnowledgeBaseUpdate) {
  return request<Api.KnowledgeBase.KnowledgeBase>({
    url: `/api/knowledge-bases/${id}`,
    method: 'put',
    data
  });
}

/**
 * 删除知识库
 */
export function deleteKnowledgeBase(id: string) {
  return request<boolean>({
    url: `/api/knowledge-bases/${id}`,
    method: 'delete'
  });
}

/**
 * 关联项目到知识库
 */
export function associateProject(kbId: string, data: { projectId: string }) {
  return request<Api.KnowledgeBase.ProjectAssociation>({
    url: `/api/knowledge-bases/${kbId}/projects`,
    method: 'post',
    data
  });
}

/**
 * 获取知识库的关联项目列表
 */
export function fetchAssociatedProjects(kbId: string) {
  return request<Api.KnowledgeBase.AssociatedProjectList>({
    url: `/api/knowledge-bases/${kbId}/projects`,
    method: 'get'
  });
}

/**
 * 取消项目关联
 */
export function disassociateProject(kbId: string, projectId: string) {
  return request<boolean>({
    url: `/api/knowledge-bases/${kbId}/projects/${projectId}`,
    method: 'delete'
  });
}
