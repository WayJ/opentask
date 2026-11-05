import { request } from '../request';

export interface ProjectTemplateMilestone {
  name: string;
  description?: string | null;
  position?: number;
  targetOffsetDays?: number | null;
}

export interface ProjectTemplatePayload {
  description?: string | null;
  milestones?: ProjectTemplateMilestone[];
}

export interface ProjectTemplateRow {
  id: string;
  workspaceId: string;
  name: string;
  description?: string | null;
  icon?: string | null;
  payload: ProjectTemplatePayload;
  sortOrder: number;
  source: string;
  seedKey?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface ProjectTemplateListResult {
  rows: ProjectTemplateRow[];
  total: number;
}

export function fetchProjectTemplates() {
  return request<ProjectTemplateListResult>({
    url: '/api/project-templates',
    method: 'get'
  });
}

export function fetchCreateProjectTemplate(body: {
  name: string;
  description?: string;
  icon?: string;
  payload?: ProjectTemplatePayload;
  sortOrder?: number;
}) {
  return request<ProjectTemplateRow>({
    url: '/api/project-templates',
    method: 'post',
    data: body
  });
}

export function fetchUpdateProjectTemplate(
  id: string,
  body: {
    name?: string;
    description?: string;
    icon?: string;
    payload?: ProjectTemplatePayload;
    sortOrder?: number;
  }
) {
  return request<ProjectTemplateRow>({
    url: `/api/project-templates/${id}`,
    method: 'patch',
    data: body
  });
}

export function fetchDeleteProjectTemplate(id: string) {
  return request<{ id: string }>({
    url: `/api/project-templates/${id}`,
    method: 'delete'
  });
}

export function fetchApplyProjectTemplate(
  id: string,
  body: { name: string; description?: string; startsAt?: string }
) {
  return request<{ project: Api.Project.Project; milestones: Api.Project.Milestone[] }>({
    url: `/api/project-templates/${id}/apply`,
    method: 'post',
    data: body
  });
}

export function fetchProjectTemplateFromProject(
  projectId: string,
  body: { name: string; description?: string; icon?: string }
) {
  return request<ProjectTemplateRow>({
    url: `/api/project-templates/from-project/${projectId}`,
    method: 'post',
    data: body
  });
}
