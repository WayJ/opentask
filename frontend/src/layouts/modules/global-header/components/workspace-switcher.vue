<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { type WorkspaceItem, fetchCreateWorkspace, fetchWorkspaceList } from '@/service/api';
import { localStg } from '@/utils/storage';
import { resolveWorkspaceSelection, usableWorkspaces } from '@/utils/workspace-selection';
import { $t } from '@/locales';

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
    const usable = usableWorkspaces(data);
    options.value = usable.map((w: WorkspaceItem) => ({ label: w.name, value: w.id }));
    const resolved = resolveWorkspaceSelection(localStg.get('workspaceId'), usable);
    if (resolved.workspaceId) {
      current.value = resolved.workspaceId;
      localStg.set('workspaceId', resolved.workspaceId);
    } else {
      current.value = null;
      localStg.remove('workspaceId');
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

async function createWorkspace(): Promise<boolean> {
  const name = newName.value.trim();
  if (!name) return false;
  const issueKey = newIssueKey.value.trim().toUpperCase() || undefined;
  const { data, error } = await fetchCreateWorkspace({ name, issueKey });
  if (error || !data) {
    window.$message?.error(error?.message || $t('page.shell.workspaceSwitcher.createFailed'));
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
      :placeholder="$t('page.shell.workspaceSwitcher.placeholder')"
      @update:value="onUpdate"
    />
    <NButton size="small" quaternary @click="showCreate = true">+</NButton>
    <NModal
      v-model:show="showCreate"
      preset="dialog"
      :title="$t('page.shell.workspaceSwitcher.createTitle')"
      :positive-text="$t('page.issueDetail.create')"
      @positive-click="createWorkspace"
    >
      <div class="flex-col gap-12px">
        <NInput v-model:value="newName" :placeholder="$t('page.shell.workspaceSwitcher.namePlaceholder')" />
        <NInput
          v-model:value="newIssueKey"
          :placeholder="$t('page.shell.workspaceSwitcher.issueKeyPlaceholder')"
          maxlength="6"
          style="text-transform: uppercase"
          @update:value="v => (newIssueKey = (v || '').toUpperCase())"
        />
        <p class="m-0 text-12px text-gray-400">{{ $t('page.shell.workspaceSwitcher.issueKeyHint') }}</p>
      </div>
    </NModal>
  </div>
</template>
