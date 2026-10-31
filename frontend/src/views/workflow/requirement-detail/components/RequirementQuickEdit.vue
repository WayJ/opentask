<!-- frontend/src/views/workflow/requirement-detail/components/RequirementQuickEdit.vue -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { NButton, NCard, NSpace } from 'naive-ui';
import {
  getRequirementPriorityTagType,
  getRequirementStatusTagType,
  requirementPriorityOptions,
  requirementStatusOptions
} from '@/constants/requirement';
import { fetchProjectList } from '@/service/api';
import { useRequirementStore } from '@/store/modules/requirement';
import type { Api } from '@/typings/api';
import EditableField from '@/components/EditableField.vue';
import CreatePGETaskModal from './CreatePGETaskModal.vue';

interface Props {
  requirement: Api.Requirement.Requirement;
}

interface Emits {
  (e: 'refresh'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const requirementStore = useRequirementStore();

// 项目列表
const projects = ref<Api.Project.Project[]>([]);
const projectsLoading = ref(false);

// 编辑状态
const editingStatus = ref(false);
const editingPriority = ref(false);
const editingProject = ref(false);

// 创建任务对话框状态
const showCreatePGETaskModal = ref(false);

// 临时值
const tempStatus = ref<Api.Requirement.RequirementStatus | null>(null);
const tempPriority = ref<Api.Requirement.Priority | null>(null);
const tempProjectId = ref<string | null>(null);

// 工具函数
const getStatusType = getRequirementStatusTagType;
const getPriorityType = getRequirementPriorityTagType;

// 状态文本
const statusText = computed(() => {
  const option = requirementStatusOptions.find(s => s.value === props.requirement.status);
  return option?.label || props.requirement.status;
});

// 优先级文本
const priorityText = computed(() => {
  if (!props.requirement.priority) return '-';
  const option = requirementPriorityOptions.find(p => p.value === props.requirement.priority);
  return option?.label || props.requirement.priority;
});

// 保存状态
async function saveStatus() {
  if (tempStatus.value === null) return;

  try {
    await requirementStore.editRequirement(props.requirement.id, {
      status: tempStatus.value
    });
    emit('refresh');
    window.$message?.success('状态更新成功');
  } catch {
    window.$message?.error('状态更新失败');
  }
}

// 取消编辑状态
function cancelEditStatus() {
  tempStatus.value = null;
}

// 保存优先级
async function savePriority() {
  if (tempPriority.value === null) return;

  try {
    await requirementStore.editRequirement(props.requirement.id, {
      priority: tempPriority.value
    });
    emit('refresh');
    window.$message?.success('优先级更新成功');
  } catch {
    window.$message?.error('优先级更新失败');
  }
}

// 取消编辑优先级
function cancelEditPriority() {
  tempPriority.value = null;
}

// 加载项目列表
async function loadProjects() {
  projectsLoading.value = true;
  try {
    const response = await fetchProjectList();
    projects.value = response.data || [];
  } catch (error) {
    console.error('Failed to load projects:', error);
    projects.value = [];
  } finally {
    projectsLoading.value = false;
  }
}

// 项目选项
const projectOptions = computed(() => {
  const options = projects.value.map(p => ({
    label: p.name,
    value: p.id
  }));
  // 添加"未归类"选项
  options.unshift({
    label: '未归类',
    value: ''
  });
  return options;
});

// 当前项目文本
const projectText = computed(() => {
  const projectId = (props.requirement as any).project_id;
  if (!projectId) return '未归类';
  const project = projects.value.find(p => p.id === projectId);
  return project?.name || '未知项目';
});

// 保存项目
async function saveProject() {
  if (tempProjectId.value === null) return;

  try {
    // 如果选择的是"未归类"（空字符串），则传递 undefined 以清空项目关联
    const projectId = tempProjectId.value === '' ? undefined : tempProjectId.value;
    await requirementStore.editRequirement(props.requirement.id, {
      project_id: projectId
    });
    emit('refresh');
    window.$message?.success('项目更新成功');
  } catch (error) {
    console.error('项目更新失败:', error);
    window.$message?.error('项目更新失败');
  }
}

// 取消编辑项目
function cancelEditProject() {
  tempProjectId.value = null;
}

// 快速操作
async function handleQuickStatus(status: Api.Requirement.RequirementStatus) {
  try {
    await requirementStore.editRequirement(props.requirement.id, { status });
    emit('refresh');
    window.$message?.success('状态更新成功');
  } catch {
    window.$message?.error('状态更新失败');
  }
}

// 组件挂载时加载项目列表
onMounted(() => {
  loadProjects();
});
</script>

<template>
  <div class="requirement-quick-edit">
    <!-- 核心属性卡片 -->
    <NCard size="small" class="sidebar-card" :bordered="false">
      <template #header>
        <div class="card-header">
          <span class="card-icon">🎯</span>
          <span>核心属性</span>
        </div>
      </template>

      <!-- 状态 -->
      <EditableField
        v-model="tempStatus"
        v-model:editing="editingStatus"
        label="状态"
        :display-value="statusText"
        :options="requirementStatusOptions"
        :tag-type="getStatusType(requirement.status)"
        @save="saveStatus"
        @cancel="cancelEditStatus"
        @start-edit="tempStatus = requirement.status"
      >
        <template #label-icon>
          <icon-mdi-checkbox-marked-circle />
        </template>
      </EditableField>

      <!-- 优先级 -->
      <EditableField
        v-model="tempPriority"
        v-model:editing="editingPriority"
        label="优先级"
        :display-value="priorityText"
        :options="requirementPriorityOptions"
        :tag-type="requirement.priority ? getPriorityType(requirement.priority) : undefined"
        placeholder="-"
        @save="savePriority"
        @cancel="cancelEditPriority"
        @start-edit="tempPriority = requirement.priority || null"
      >
        <template #label-icon>
          <icon-mdi-flag />
        </template>
      </EditableField>

      <!-- 创建时间 -->
      <EditableField
        v-model="tempStatus"
        v-model:editing="editingStatus"
        label="创建时间"
        :display-value="new Date(requirement.created_at).toLocaleString()"
        :readonly="true"
      >
        <template #label-icon>
          <icon-mdi-clock-outline />
        </template>
      </EditableField>

      <!-- 所属项目 -->
      <EditableField
        v-model="tempProjectId"
        v-model:editing="editingProject"
        label="所属项目"
        :display-value="projectText"
        :options="projectOptions"
        :loading="projectsLoading"
        select-width="140px"
        :clearable="true"
        placeholder="未归类"
        @save="saveProject"
        @cancel="cancelEditProject"
        @start-edit="tempProjectId = (requirement as any).project_id || ''"
      >
        <template #label-icon>
          <icon-mdi-folder-outline />
        </template>
      </EditableField>
    </NCard>

    <!-- 快速操作卡片 -->
    <NCard size="small" class="sidebar-card" :bordered="false">
      <template #header>
        <div class="card-header">
          <span class="card-icon">⚡</span>
          <span>快速操作</span>
        </div>
      </template>
      <NSpace vertical :size="8">
        <!-- 新增：创建任务按钮 -->
        <NButton block secondary type="primary" @click="showCreatePGETaskModal = true">
          <template #icon>
            <icon-mdi-plus-circle />
          </template>
          创建任务
        </NButton>
        <NButton
          v-if="requirement.status !== 'generating'"
          block
          secondary
          type="success"
          @click="handleQuickStatus('generating')"
        >
          <template #icon>
            <icon-mdi-play />
          </template>
          设为生成中
        </NButton>
        <NButton
          v-if="requirement.status !== 'completed'"
          block
          secondary
          type="info"
          @click="handleQuickStatus('completed')"
        >
          <template #icon>
            <icon-mdi-check-circle />
          </template>
          标记完成
        </NButton>
        <NButton v-if="requirement.status !== 'planning'" block secondary @click="handleQuickStatus('planning')">
          <template #icon>
            <icon-mdi-file-document />
          </template>
          设为规划中
        </NButton>
      </NSpace>
    </NCard>

    <!-- 创建Agent任务对话框 -->
    <CreatePGETaskModal
      v-model:show="showCreatePGETaskModal"
      :requirement-id="requirement.id"
      :requirement-title="requirement.title"
      @success="emit('refresh')"
    />
  </div>
</template>

<style scoped>
.requirement-quick-edit {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.sidebar-card {
  box-shadow: var(--shadow-sm);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-weight: 500;
}

.card-icon {
  font-size: 18px;
}
</style>
