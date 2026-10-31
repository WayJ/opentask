import { request } from '../request';

/**
 * 获取知识文档列表
 */
export function fetchKnowledgeList(params?: Api.Knowledge.KnowledgeSearchParams) {
  return request<Api.Knowledge.KnowledgeList>({
    url: '/api/knowledge',
    method: 'get',
    params
  });
}

/**
 * 获取知识文档详情
 */
export function fetchKnowledgeDetail(id: string) {
  return request<Api.Knowledge.Knowledge>({
    url: `/api/knowledge/${id}`,
    method: 'get'
  });
}

/**
 * 创建知识文档
 */
export function createKnowledge(data: Api.Knowledge.KnowledgeCreate) {
  return request<Api.Knowledge.Knowledge>({
    url: '/api/knowledge',
    method: 'post',
    data
  });
}

/**
 * 更新知识文档
 */
export function updateKnowledge(id: string, data: Api.Knowledge.KnowledgeUpdate) {
  return request<Api.Knowledge.Knowledge>({
    url: `/api/knowledge/${id}`,
    method: 'put',
    data
  });
}

/**
 * 删除知识文档
 */
export function deleteKnowledge(id: string) {
  return request<boolean>({
    url: `/api/knowledge/${id}`,
    method: 'delete'
  });
}

/**
 * 点赞知识文档
 */
export function likeKnowledge(id: string) {
  return request<boolean>({
    url: `/api/knowledge/${id}/like`,
    method: 'post'
  });
}

// ============================================================================
// Git 编辑相关 API
// ============================================================================

/**
 * 获取文档原始 Markdown 内容（从 Git 仓库）
 */
export function fetchDocumentRawContent(kbId: string, docId: string) {
  return request<string>({
    url: `/api/knowledge/kb/${kbId}/documents/${docId}/raw`,
    method: 'get',
    responseType: 'text'
  });
}

/**
 * 提交文档到 Git 仓库
 */
export function commitDocument(kbId: string, docId: string, data: Api.Knowledge.DocumentCommit) {
  return request<Api.Knowledge.CommitResult>({
    url: `/api/knowledge/kb/${kbId}/documents/${docId}/commit`,
    method: 'post',
    data
  });
}

/**
 * 获取文档历史记录
 */
export function fetchDocumentHistory(kbId: string, docId: string, limit: number = 10) {
  return request<Api.Knowledge.DocumentHistory[]>({
    url: `/api/knowledge/kb/${kbId}/documents/${docId}/history`,
    method: 'get',
    params: { limit }
  });
}

/**
 * 获取文档 diff
 */
export function fetchDocumentDiff(kbId: string, docId: string, params?: Api.Knowledge.DiffParams) {
  return request<Api.Knowledge.DocumentDiff>({
    url: `/api/knowledge/kb/${kbId}/documents/${docId}/diff`,
    method: 'get',
    params
  });
}

/**
 * 获取知识库 Git 状态
 */
export function fetchKnowledgeBaseStatus(kbId: string) {
  return request<Api.Knowledge.GitStatus>({
    url: `/api/knowledge/kb/${kbId}/status`,
    method: 'get'
  });
}

/**
 * 创建新分支
 */
export function createBranch(kbId: string, data: Api.Knowledge.CreateBranchParams) {
  return request<Api.Knowledge.BranchResult>({
    url: `/api/knowledge/kb/${kbId}/branches`,
    method: 'post',
    data
  });
}

/**
 * 创建 Pull Request
 */
export function createPullRequest(kbId: string, data: Api.Knowledge.CreatePRParams) {
  return request<Api.Knowledge.PRResult>({
    url: `/api/knowledge/kb/${kbId}/pull-requests`,
    method: 'post',
    data
  });
}
