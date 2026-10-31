import { reactive, ref } from 'vue';
import { defineStore } from 'pinia';
import {
  assignRequirement,
  createRequirement,
  deleteRequirement,
  fetchRequirementDetail,
  fetchRequirementList,
  fetchRequirementStats,
  fetchRequirementTimeline,
  fetchRequirementWithEvents,
  updateRequirement
} from '@/service/api';

export const useRequirementStore = defineStore('requirement', () => {
  const requirements = ref<Api.Requirement.Requirement[]>([]);
  const currentRequirement = ref<Api.Requirement.RequirementWithEvents | null>(null);
  const timeline = ref<Api.Requirement.Timeline | null>(null);
  const stats = ref<Api.Requirement.Statistics | null>(null);
  const loading = ref(false);
  const pagination = reactive({
    total: 0,
    page: 1,
    pageSize: 20
  });

  /**
   * Get requirement list
   */
  async function getRequirements(params?: {
    status?: Api.Requirement.RequirementStatus;
    priority?: Api.Requirement.Priority;
    assignee_id?: string;
    project_id?: string;
    page?: number;
    page_size?: number;
  }) {
    loading.value = true;
    try {
      const response = await fetchRequirementList({
        ...params,
        page: params?.page || pagination.page,
        page_size: params?.page_size || pagination.pageSize
      });
      // 后端返回 {data: {data: [], total, page, page_size}}
      const data = response.data;
      requirements.value = data.data || [];
      pagination.total = data.total || 0;
      pagination.page = data.page || 1;
      pagination.pageSize = data.page_size || 20;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Get requirement detail
   */
  async function getRequirement(id: string) {
    loading.value = true;
    try {
      const response = await fetchRequirementDetail(id);
      return response.data;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Get requirement with events
   */
  async function getRequirementWithEvents(id: string) {
    loading.value = true;
    try {
      const response = await fetchRequirementWithEvents(id);
      currentRequirement.value = response.data;
      return response.data;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Get requirement timeline
   */
  async function getTimeline(id: string) {
    loading.value = true;
    try {
      const response = await fetchRequirementTimeline(id);
      timeline.value = response.data;
      return response.data;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Create requirement
   */
  async function addRequirement(data: Api.Requirement.CreateRequirement) {
    const response = await createRequirement(data);
    const requirement = response.data;
    requirements.value.unshift(requirement);
    return requirement;
  }

  /**
   * Update requirement
   */
  async function editRequirement(id: string, data: Api.Requirement.UpdateRequirement) {
    const response = await updateRequirement(id, data);
    const requirement = response.data;
    const index = requirements.value.findIndex(r => r.id === id);
    if (index !== -1) {
      requirements.value[index] = requirement;
    }
    if (currentRequirement.value?.id === id) {
      currentRequirement.value = requirement;
    }
    return requirement;
  }

  /**
   * Delete requirement
   */
  async function removeRequirement(id: string) {
    await deleteRequirement(id);
    requirements.value = requirements.value.filter(r => r.id !== id);
    if (currentRequirement.value?.id === id) {
      currentRequirement.value = null;
    }
  }

  /**
   * Assign requirement
   */
  async function assignReq(id: string, data: Api.Requirement.AssignRequest) {
    const response = await assignRequirement(id, data);
    const requirement = response.data;
    const index = requirements.value.findIndex(r => r.id === id);
    if (index !== -1) {
      requirements.value[index] = requirement;
    }
    if (currentRequirement.value?.id === id) {
      currentRequirement.value = requirement;
    }
    return requirement;
  }

  /**
   * Get statistics
   */
  async function getStats() {
    const response = await fetchRequirementStats();
    stats.value = response.data;
    return response.data;
  }

  return {
    requirements,
    currentRequirement,
    timeline,
    stats,
    loading,
    pagination,
    getRequirements,
    getRequirement,
    getRequirementWithEvents,
    getTimeline,
    addRequirement,
    editRequirement,
    removeRequirement,
    assignReq,
    getStats
  };
});
