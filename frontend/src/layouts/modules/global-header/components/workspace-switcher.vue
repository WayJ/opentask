<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { type WorkspaceItem, fetchCreateWorkspace, fetchWorkspaceList } from '@/service/api';
import { localStg } from '@/utils/storage';

defineOptions({ name: 'WorkspaceSwitcher' });

const loading = ref(false);
const options = ref<{ label: string; value: string }[]>([]);
const current = ref<string | null>(localStg.get('workspaceId') || null);
const showCreate = ref(false);
const newName = ref('');

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchWorkspaceList();
    if (error || !data) return;
    options.value = data.map((w: WorkspaceItem) => ({ label: w.name, value: w.id }));
    if (!current.value && data.length) {
      current.value = data[0].id;
      localStg.set('workspaceId', data[0].id);
    }
  } finally {
    loading.value = false;
  }
}

function onUpdate(value: string) {
  current.value = value;
  localStg.set('workspaceId', value);
  // 简单刷新以让列表按新区加载
  window.location.reload();
}

async function createWorkspace() {
  const name = newName.value.trim();
  if (!name) return;
  const { data, error } = await fetchCreateWorkspace({ name });
  if (error || !data) {
    window.$message?.error(error?.message || '创建失败');
    return;
  }
  showCreate.value = false;
  newName.value = '';
  await load();
  onUpdate(data.id);
}

onMounted(load);
</script>

<template>
  <div class="mr-8px flex-y-center gap-8px">
    <NSelect
      :value="current"
      :options="options"
      :loading="loading"
      size="small"
      class="w-180px"
      placeholder="工作区"
      @update:value="onUpdate"
    />
    <NButton size="small" quaternary @click="showCreate = true">+</NButton>
    <NModal
      v-model:show="showCreate"
      preset="dialog"
      title="创建工作区"
      positive-text="创建"
      @positive-click="createWorkspace"
    >
      <NInput v-model:value="newName" placeholder="工作区名称" />
    </NModal>
  </div>
</template>
