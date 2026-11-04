/** Tag / Label API 客户端（E7-S1） */
import { request } from '@/service/request';

export interface TagItem {
  id: number;
  workspaceId: string;
  name: string;
  color: string;
  groupId?: string | null;
  createdAt?: string;
  updatedAt?: string;
}

export interface TagGroupItem {
  id: string;
  workspaceId: string;
  name: string;
  color?: string | null;
  position: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface TagBrief {
  id: number;
  name: string;
  color: string;
  groupId?: string | null;
}

export const tagApi = {
  list: (params?: { group_id?: string; q?: string }) =>
    request<{ rows: TagItem[]; total: number }>({
      url: '/api/tags',
      method: 'GET',
      params
    }),

  get: (id: number) =>
    request<TagItem>({
      url: `/api/tags/${id}`,
      method: 'GET'
    }),

  create: (data: { name: string; color?: string; group_id?: string | null }) =>
    request<TagItem>({
      url: '/api/tags',
      method: 'POST',
      data
    }),

  update: (id: number, data: { name?: string; color?: string; group_id?: string | null; clear_group?: boolean }) =>
    request<TagItem>({
      url: `/api/tags/${id}`,
      method: 'PATCH',
      data
    }),

  remove: (id: number) =>
    request<null>({
      url: `/api/tags/${id}`,
      method: 'DELETE'
    }),

  listGroups: () =>
    request<{ rows: TagGroupItem[]; total: number }>({
      url: '/api/tag-groups',
      method: 'GET'
    }),

  createGroup: (data: { name: string; color?: string; position?: number }) =>
    request<TagGroupItem>({
      url: '/api/tag-groups',
      method: 'POST',
      data
    }),

  updateGroup: (id: string, data: { name?: string; color?: string; position?: number }) =>
    request<TagGroupItem>({
      url: `/api/tag-groups/${id}`,
      method: 'PATCH',
      data
    }),

  removeGroup: (id: string) =>
    request<null>({
      url: `/api/tag-groups/${id}`,
      method: 'DELETE'
    })
};

/** @deprecated use tagApi */
export const fetchTags = tagApi.list;
