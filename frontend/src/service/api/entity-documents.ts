import { request } from '../request';

export type EntityDocParentType = 'issue' | 'project' | 'initiative';

export interface EntityDocumentRow {
  id: string;
  workspaceId: string;
  parentType: EntityDocParentType;
  parentId: string;
  title: string;
  bodyMd: string;
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface EntityDocumentListResult {
  rows: EntityDocumentRow[];
  total: number;
}

export function fetchEntityDocuments(parentType: EntityDocParentType, parentId: string) {
  return request<EntityDocumentListResult>({
    url: '/api/entity-documents',
    method: 'get',
    params: { parentType, parentId }
  });
}

export function fetchCreateEntityDocument(body: {
  parentType: EntityDocParentType;
  parentId: string;
  title: string;
  bodyMd?: string;
}) {
  return request<EntityDocumentRow>({
    url: '/api/entity-documents',
    method: 'post',
    data: body
  });
}

export function fetchUpdateEntityDocument(id: string, body: { title?: string; bodyMd?: string }) {
  return request<EntityDocumentRow>({
    url: `/api/entity-documents/${id}`,
    method: 'patch',
    data: body
  });
}

export function fetchDeleteEntityDocument(id: string) {
  return request<{ id: string }>({
    url: `/api/entity-documents/${id}`,
    method: 'delete'
  });
}
