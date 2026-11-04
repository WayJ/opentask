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
const newIssueKey = ref('');

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
  window.location.reload();
}

async function createWorkspace() {
  const name = newName.value.trim();
  if (!name) return;
  const issueKey = newIssueKey.value.trim().toUpperCase() || undefined;
  const { data, error } = await fetchCreateWorkspace({ name, issueKey });
  if (error || !data) {
    window.$message?.error(error?.message || '创建失败');
    return false;
  }
  showCreate.value = false;
  newName.value = '';
  newIssueKey.value = '';
  await load();
  onUpdate(data.id);
  return true;
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
      <div class="flex-col gap-12px">
        <NInput v-model:value="newName" placeholder="工作区名称" />
        <NInput
          v-model:value="newIssueKey"
          placeholder="Issue Key（可选，2–6 位大写）"
          maxlength="6"
          style="text-transform: uppercase"
          @update:value="v => (newIssueKey = (v || '').toUpperCase())"
        />
        <p class="m-0 text-12px text-gray-400">留空则从名称自动生成；创建后可在 Cycles 设置中修改。</p>
      </div>
    </NModal>
  </div>
</template>
