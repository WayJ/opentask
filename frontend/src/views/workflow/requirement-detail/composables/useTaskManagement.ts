import { type ComputedRef, computed, ref } from 'vue';
import type { UploadFileInfo } from 'naive-ui';
import type { Task } from '@/service/api/requirement';
import {
  RequirementTaskStatusMap,
  RequirementTaskTypeMap,
  completeRequirementTask,
  createRequirementTask,
  deleteRequirementTask,
  fetchRequirementTaskList,
  importRequirementTasks,
  startRequirementTask,
  updateRequirementTask
} from '@/service/api/requirement';

export function useTaskManagement(requirementId: ComputedRef<string>) {
  // 任务数据
  const tasks = ref<Task[]>([]);
  const tasksLoading = ref(false);

  // 创建任务模态框
  const showCreateModal = ref(false);
  const showCreateSubTaskModal = ref(false);
  const parentTaskForSub = ref<Task | null>(null);
  const createForm = ref({
    title: '',
    description: '',
    task_type: 'IMPLEMENT' as const
  });

  // 编辑任务模态框
  const showEditModal = ref(false);
  const editTask = ref<Task | null>(null);
  const editForm = ref({
    title: '',
    description: '',
    status: '' as Task['status'] | ''
  });

  // 导入任务相关
  const importUploading = ref(false);
  const importResult = ref<{ imported_count: number; failed_count: number; errors: string[] } | null>(null);
  const showImportResult = ref(false);

  // 任务类型选项
  const taskTypeOptions = Object.entries(RequirementTaskTypeMap).map(([value, label]) => ({
    value,
    label
  }));

  // 任务状态选项
  const taskStatusOptions = Object.entries(RequirementTaskStatusMap).map(([value, label]) => ({
    value,
    label
  }));

  // 使用后端返回的树形结构，只需过滤出根任务
  const taskTree = computed(() => {
    // 后端 API 已经返回了树形结构（children 字段已填充）
    // 我们只需要过滤出根任务（没有 parent_id 的任务）
    const rootTasks = tasks.value.filter(task => !task.parent_id);

    // 按 code 排序（任务需要按顺序依次完成）
    const sortByCode = (a: Task, b: Task) => {
      const aCode = a.code ? Number.parseInt(a.code, 10) : 0;
      const bCode = b.code ? Number.parseInt(b.code, 10) : 0;
      return aCode - bCode;
    };
    rootTasks.sort(sortByCode);

    // 递归排序子任务
    const sortChildren = (task: Task) => {
      if (task.children && task.children.length > 0) {
        task.children.sort(sortByCode);
        task.children.forEach(sortChildren);
      }
    };
    rootTasks.forEach(sortChildren);

    return rootTasks;
  });

  // 计算任务进度
  const taskProgress = computed(() => {
    const allTasks = tasks.value;
    const total = allTasks.length;
    const completed = allTasks.filter(t => t.status === 'COMPLETED').length;
    const inProgress = allTasks.filter(t => t.status === 'RUNNING').length;
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;

    return {
      total,
      completed,
      inProgress,
      percentage
    };
  });

  // 加载任务列表
  async function loadTasks() {
    tasksLoading.value = true;
    try {
      const response = await fetchRequirementTaskList(requirementId.value);

      // 处理不同的响应格式
      let taskList;
      if (response && typeof response === 'object') {
        if ('rows' in response) {
          taskList = response.rows;
        } else if ('data' in response && response.data && 'rows' in response.data) {
          taskList = response.data.rows;
        } else if (Array.isArray(response)) {
          taskList = response;
        } else {
          taskList = [];
        }
      } else {
        taskList = [];
      }

      tasks.value = Array.isArray(taskList) ? taskList : [];
    } catch {
      window.$message?.error('加载任务失败');
      tasks.value = [];
    } finally {
      tasksLoading.value = false;
    }
  }

  // 打开创建子任务模态框
  function openCreateSubTaskModal(parentTask: Task) {
    parentTaskForSub.value = parentTask;
    createForm.value = { title: '', description: '', task_type: 'IMPLEMENT' };
    showCreateSubTaskModal.value = true;
  }

  // 创建任务
  async function handleCreateTask() {
    try {
      await createRequirementTask({
        requirement_id: requirementId.value,
        ...createForm.value
      });
      showCreateModal.value = false;
      createForm.value = { title: '', description: '', task_type: 'IMPLEMENT' };
      await loadTasks();
    } catch {
      window.$message?.error('创建任务失败');
    }
  }

  // 创建子任务
  async function handleCreateSubTask() {
    if (!parentTaskForSub.value) return;
    try {
      await createRequirementTask({
        requirement_id: requirementId.value,
        parent_id: parentTaskForSub.value.id,
        ...createForm.value
      });
      showCreateSubTaskModal.value = false;
      createForm.value = { title: '', description: '', task_type: 'IMPLEMENT' };
      await loadTasks();
    } catch {
      window.$message?.error('创建子任务失败');
    }
  }

  // 打开编辑任务
  function openEditModal(task: Task) {
    editTask.value = task;
    editForm.value = {
      title: task.title,
      description: task.description || '',
      status: task.status as Task['status']
    };
    showEditModal.value = true;
  }

  // 更新任务
  async function handleUpdateTask() {
    if (!editTask.value) return;
    try {
      // 过滤掉空字符串的 status
      const updateData = {
        title: editForm.value.title,
        description: editForm.value.description,
        ...(editForm.value.status && { status: editForm.value.status })
      };
      await updateRequirementTask(editTask.value.id, updateData);
      showEditModal.value = false;
      await loadTasks();
    } catch {
      window.$message?.error('更新任务失败');
    }
  }

  // 删除任务
  async function handleDeleteTask(taskId: string) {
    try {
      await deleteRequirementTask(requirementId.value, taskId);
      await loadTasks();
    } catch {
      window.$message?.error('删除任务失败');
    }
  }

  // 开始任务
  async function handleStartTask(task: Task) {
    try {
      await startRequirementTask(task.id);
      await loadTasks();
    } catch (error: any) {
      window.$message?.error(error.response?.data?.message || `无法开始任务:${error.message}`);
    }
  }

  // 完成任务
  async function handleCompleteTask(task: Task) {
    try {
      await completeRequirementTask(task.id);
      await loadTasks();
    } catch {
      window.$message?.error('完成任务失败');
    }
  }

  // 批量导入任务
  async function handleImportTasks(options: { file: UploadFileInfo }) {
    const file = options.file.file;
    if (!file) return;

    importUploading.value = true;
    try {
      const result = (await importRequirementTasks(requirementId.value, file)) as any;
      importResult.value = {
        imported_count: result.imported_count,
        failed_count: result.failed_count,
        errors: result.errors
      };
      showImportResult.value = true;
      await loadTasks();
    } catch (error: any) {
      window.$message?.error(error.response?.data?.message || `导入失败: ${error.message}`);
    } finally {
      importUploading.value = false;
    }
  }

  return {
    // 状态
    tasks,
    tasksLoading,
    showCreateModal,
    showCreateSubTaskModal,
    parentTaskForSub,
    createForm,
    showEditModal,
    editTask,
    editForm,
    importUploading,
    importResult,
    showImportResult,
    // 计算属性
    taskTypeOptions,
    taskStatusOptions,
    taskTree,
    taskProgress,
    // 方法
    loadTasks,
    openCreateSubTaskModal,
    handleCreateTask,
    handleCreateSubTask,
    openEditModal,
    handleUpdateTask,
    handleDeleteTask,
    handleStartTask,
    handleCompleteTask,
    handleImportTasks
  };
}
