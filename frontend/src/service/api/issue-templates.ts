import { request } from '../request';

export interface IssueTemplatePayload {
  title?: string;
  description?: string;
  type?: string;
  priority?: string;
  labelIds?: string[];
  projectId?: string;
  fields?: Array<{
    name: string;
    label: string;
    type: 'text' | 'textarea' | 'select' | 'checkbox';
    placeholder?: string;
    required: boolean;
    options?: string[];
    defaultValue?: string | boolean;
  }>;
}

export interface IssueTemplateRow {
  id: string;
  workspaceId: string;
  name: string;
  description?: string | null;
  icon?: string | null;
  payload: IssueTemplatePayload;
  sortOrder: number;
  source: string;
  seedKey?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface IssueTemplateListResult {
  rows: IssueTemplateRow[];
  total: number;
}

export function fetchIssueTemplates() {
  return request<IssueTemplateListResult>({
    url: '/api/issue-templates',
    method: 'get'
  });
}

export function fetchCreateIssueTemplate(body: {
  name: string;
  description?: string;
  icon?: string;
  payload?: IssueTemplatePayload;
  sortOrder?: number;
}) {
  return request<IssueTemplateRow>({
    url: '/api/issue-templates',
    method: 'post',
    data: body
  });
}

export function fetchUpdateIssueTemplate(
  id: string,
  body: {
    name?: string;
    description?: string;
    icon?: string;
    payload?: IssueTemplatePayload;
    sortOrder?: number;
  }
) {
  return request<IssueTemplateRow>({
    url: `/api/issue-templates/${id}`,
    method: 'patch',
    data: body
  });
}

export function fetchDeleteIssueTemplate(id: string) {
  return request<{ id: string }>({
    url: `/api/issue-templates/${id}`,
    method: 'delete'
  });
}
