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
 * Milestone API (E8-S1)
 */

/** List milestones for a project */
export function fetchProjectMilestones(projectId: string) {
  return request<Api.Project.Milestone[]>({
    url: `/api/projects/${projectId}/milestones`,
    method: 'get'
  });
}

/** Create milestone */
export function createProjectMilestone(projectId: string, data: Api.Project.CreateMilestone) {
  return request<Api.Project.Milestone>({
    url: `/api/projects/${projectId}/milestones`,
    method: 'post',
    data
  });
}

/** Update milestone */
export function updateProjectMilestone(projectId: string, milestoneId: string, data: Api.Project.UpdateMilestone) {
  return request<Api.Project.Milestone>({
    url: `/api/projects/${projectId}/milestones/${milestoneId}`,
    method: 'patch',
    data
  });
}

/** Delete milestone */
export function deleteProjectMilestone(projectId: string, milestoneId: string) {
  return request({
    url: `/api/projects/${projectId}/milestones/${milestoneId}`,
    method: 'delete'
  });
}

/**
 * Project API object
 * @example
 * import { projectApi } from '@/service/api/project';
 * const projects = await projectApi.getList();
 */

/**
 * Health / Watchers / Timeline (E8-S2)
 */

export function fetchProjectHealth(projectId: string, history = false) {
  return request<Api.Project.HealthPayload>({
    url: `/api/projects/${projectId}/health`,
    method: 'get',
    params: history ? { history: 1 } : undefined
  });
}

export function postProjectHealth(projectId: string, data: { status: string; note?: string | null }) {
  return request<Api.Project.HealthUpdate>({
    url: `/api/projects/${projectId}/health`,
    method: 'post',
    data
  });
}

export function fetchProjectWatchers(projectId: string) {
  return request<Api.Project.ProjectWatcher[]>({
    url: `/api/projects/${projectId}/watchers`,
    method: 'get'
  });
}

export function watchProject(projectId: string) {
  return request<Api.Project.ProjectWatcher>({
    url: `/api/projects/${projectId}/watchers`,
    method: 'post'
  });
}

export function unwatchProject(projectId: string) {
  return request({
    url: `/api/projects/${projectId}/watchers`,
    method: 'delete'
  });
}

export function fetchProjectTimeline(projectId: string) {
  return request<Api.Project.TimelineData>({
    url: `/api/projects/${projectId}/timeline`,
    method: 'get'
  });
}

export const projectApi = {
  getList: fetchProjectList,
  getDetail: fetchProjectDetail,
  create: createProject,
  update: updateProject,
  delete: deleteProject,
  getRepos: fetchProjectRepos,
  createRepoConfig,
  updateRepoConfig,
  deleteRepoConfig,
  getMilestones: fetchProjectMilestones,
  createMilestone: createProjectMilestone,
  updateMilestone: updateProjectMilestone,
  deleteMilestone: deleteProjectMilestone,
  getHealth: fetchProjectHealth,
  postHealth: postProjectHealth,
  getWatchers: fetchProjectWatchers,
  watch: watchProject,
  unwatch: unwatchProject,
  getTimeline: fetchProjectTimeline
};
