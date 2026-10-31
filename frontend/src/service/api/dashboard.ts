/** Dashboard API */
import { request } from '@/service/request';

/**
 * 获取研发效能看板总览数据
 */
export function fetchDashboardOverview(projectId?: string) {
  return request<Api.Dashboard.DashboardOverview>({
    url: '/api/dashboard/overview',
    method: 'get',
    params: projectId ? { project_id: projectId } : undefined
  });
}
