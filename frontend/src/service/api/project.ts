import { request } from '../request';

/**
 * Project API
 */

/** Get project list */
export function fetchProjectList() {
  return request<Api.Project.Project[]>({
    url: '/api/projects',
    method: 'get'
  });
}

/** Get project detail */
export function fetchProjectDetail(id: string) {
  return request<Api.Project.Project>({
    url: `/api/projects/${id}`,
    method: 'get'
  });
}

/** Create project */
export function createProject(data: Api.Project.CreateProject) {
  return request<Api.Project.Project>({
    url: '/api/projects',
    method: 'post',
    data
  });
}

/** Update project */
export function updateProject(id: string, data: Api.Project.UpdateProject) {
  return request<Api.Project.Project>({
    url: `/api/projects/${id}`,
    method: 'put',
    data
  });
}

/** Delete project */
export function deleteProject(id: string) {
  return request({
    url: `/api/projects/${id}`,
    method: 'delete'
  });
}

/**
 * Repo Config API
 */

/** Get repo configs by project */
export function fetchProjectRepos(projectId: string) {
  return request<Api.Project.RepoConfig[]>({
    url: `/api/projects/${projectId}/repos`,
    method: 'get'
  });
}

/** Create repo config */
export function createRepoConfig(projectId: string, data: Api.Project.CreateRepoConfig) {
  return request<Api.Project.RepoConfig>({
    url: `/api/projects/${projectId}/repos`,
    method: 'post',
    data
  });
}

/** Update repo config */
export function updateRepoConfig(projectId: string, repoId: number, data: Partial<Api.Project.CreateRepoConfig>) {
  return request<Api.Project.RepoConfig>({
    url: `/api/projects/${projectId}/repos/${repoId}`,
    method: 'put',
    data
  });
}

/** Delete repo config */
export function deleteRepoConfig(projectId: string, repoId: number) {
  return request({
    url: `/api/projects/${projectId}/repos/${repoId}`,
    method: 'delete'
  });
}

/**
 * Project API object
 * @example
 * import { projectApi } from '@/service/api/project';
 * const projects = await projectApi.getList();
 */
export const projectApi = {
  getList: fetchProjectList,
  getDetail: fetchProjectDetail,
  create: createProject,
  update: updateProject,
  delete: deleteProject,
  getRepos: fetchProjectRepos,
  createRepoConfig,
  updateRepoConfig,
  deleteRepoConfig
};
