<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NButton, NDivider, NEmpty, NModal, NSelect, NSpace, NTag, useMessage } from 'naive-ui';
import { associateProject, disassociateProject, fetchAssociatedProjects } from '@/service/api/knowledge-base';
import { fetchProjectList } from '@/service/api/project';
import type { Api } from '@/typings/api';

interface Props {
  visible: boolean;
  knowledgeBase: Api.KnowledgeBase.KnowledgeBase | null;
}

interface Emits {
  (e: 'update:visible', value: boolean): void;
  (e: 'success'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const message = useMessage();
const loadingProjects = ref(false);
const associatedProjects = ref<Api.KnowledgeBase.AssociatedProject[]>([]);
const selectedProjectId = ref<string | null>(null);
const availableProjects = ref<Api.Project.Project[]>([]);

// 可用项目选项
const availableProjectOptions = computed(() => {
  const associatedIds = associatedProjects.value.map(p => p.projectId);
  return availableProjects.value
    .filter(p => !associatedIds.includes(p.id))
    .map(p => ({
      label: p.name,
      value: p.id
    }));
});

// 加载已关联项目
const loadAssociatedProjects = async () => {
  if (!props.knowledgeBase) return;

  try {
    const { data } = await fetchAssociatedProjects(props.knowledgeBase.id);
    associatedProjects.value = data.rows;
  } catch (error) {
    message.error('加载关联项目失败');
    // eslint-disable-next-line no-console
    console.error(error);
  }
};

// 加载可用项目列表
const loadAvailableProjects = async () => {
  loadingProjects.value = true;
  try {
    const { data } = await fetchProjectList();
    availableProjects.value = data;
  } catch (error) {
    message.error('加载项目列表失败');
    // eslint-disable-next-line no-console
    console.error(error);
  } finally {
    loadingProjects.value = false;
  }
};

// 关联项目
const handleAssociate = async () => {
  if (!props.knowledgeBase || !selectedProjectId.value) return;

  try {
    await associateProject(props.knowledgeBase.id, {
      projectId: selectedProjectId.value
    });
    message.success('关联成功');
    selectedProjectId.value = null;
    await loadAssociatedProjects();
    emit('success');
  } catch (error) {
    message.error('关联失败');
    // eslint-disable-next-line no-console
    console.error(error);
  }
};

// 取消关联
const handleDisassociate = async (project: Api.KnowledgeBase.AssociatedProject) => {
  try {
    await disassociateProject(props.knowledgeBase!.id, project.projectId);
    message.success('取消关联成功');
    await loadAssociatedProjects();
    emit('success');
  } catch (error) {
    message.error('取消关联失败');
    // eslint-disable-next-line no-console
    console.error(error);
  }
};

// 关闭对话框
const handleClose = () => {
  emit('update:visible', false);
};

// 监听知识库变化
watch(
  () => props.knowledgeBase,
  kb => {
    if (kb) {
      loadAssociatedProjects();
      loadAvailableProjects();
    } else {
      associatedProjects.value = [];
      availableProjects.value = [];
    }
  }
);
</script>

<template>
  <NModal :show="visible" title="关联项目" :mask-closable="false" style="width: 700px" @update:show="handleClose">
    <div class="project-association">
      <div class="associated-section">
        <h3>已关联项目</h3>
        <NSpace v-if="associatedProjects.length > 0" vertical :size="12">
          <NTag
            v-for="project in associatedProjects"
            :key="project.id"
            closable
            type="success"
            size="medium"
            @close="handleDisassociate(project)"
          >
            {{ project.name }}
          </NTag>
        </NSpace>
        <NEmpty v-else description="暂无关联项目" size="small" />
      </div>

      <NDivider />

      <div class="available-section">
        <h3>添加关联</h3>
        <NSelect
          v-model:value="selectedProjectId"
          :options="availableProjectOptions"
          placeholder="选择要关联的项目"
          filterable
          :loading="loadingProjects"
          style="width: 100%; margin-bottom: 12px"
        />
        <NButton type="primary" :disabled="!selectedProjectId" block @click="handleAssociate">关联项目</NButton>
      </div>
    </div>

    <template #footer>
      <NSpace>
        <NButton @click="handleClose">关闭</NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped lang="scss">
.project-association {
  .associated-section {
    margin-bottom: 20px;

    h3 {
      font-size: 16px;
      font-weight: 600;
      margin: 0 0 12px 0;
      color: #333;
    }
  }

  .available-section {
    h3 {
      font-size: 16px;
      font-weight: 600;
      margin: 0 0 12px 0;
      color: #333;
    }
  }
}
</style>
