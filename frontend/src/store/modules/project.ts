import { ref } from 'vue';
import { defineStore } from 'pinia';
import { createProject, deleteProject, fetchProjectDetail, fetchProjectList, updateProject } from '@/service/api';

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Api.Project.Project[]>([]);
  const currentProject = ref<Api.Project.Project | null>(null);
  const loading = ref(false);

  /**
   * Get all projects
   */
  async function getProjects() {
    loading.value = true;
    try {
      const response = await fetchProjectList();
      projects.value = response.data || [];
    } finally {
      loading.value = false;
    }
  }

  /**
   * Get project detail
   */
  async function getProject(id: string) {
    loading.value = true;
    try {
      const response = await fetchProjectDetail(id);
      currentProject.value = response.data;
      return response.data;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Create project
   */
  async function addProject(data: Api.Project.CreateProject) {
    const response = await createProject(data);
    const project = response.data;
    projects.value.unshift(project);
    return project;
  }

  /**
   * Update project
   */
  async function editProject(id: string, data: Api.Project.UpdateProject) {
    const response = await updateProject(id, data);
    const project = response.data;
    const index = projects.value.findIndex(p => p.id === id);
    if (index !== -1) {
      projects.value[index] = project;
    }
    if (currentProject.value?.id === id) {
      currentProject.value = project;
    }
    return project;
  }

  /**
   * Delete project
   */
  async function removeProject(id: string) {
    await deleteProject(id);
    projects.value = projects.value.filter(p => p.id !== id);
    if (currentProject.value?.id === id) {
      currentProject.value = null;
    }
  }

  return {
    projects,
    currentProject,
    loading,
    getProjects,
    getProject,
    addProject,
    editProject,
    removeProject
  };
});
