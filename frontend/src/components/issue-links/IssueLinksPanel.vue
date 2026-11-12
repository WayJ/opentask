<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { NButton, NCard, NEmpty, NInput, NSpace, NSpin, NText } from 'naive-ui';
import {
  type IssueLink,
  createIssueLink,
  deleteIssueLink,
  fetchIssueLinks,
  patchIssueLink
} from '@/service/api/issue-links';
import { hostnameFromUrl, isHttpUrl } from '@/utils/issueLinkUrl';
import { $t } from '@/locales';

const props = defineProps<{
  issueId: string;
}>();

defineOptions({ name: 'IssueLinksPanel' });

const loading = ref(false);
const saving = ref(false);
const rows = ref<IssueLink[]>([]);
const newUrl = ref('');
const newTitle = ref('');
const editingId = ref<string | null>(null);
const editUrl = ref('');
const editTitle = ref('');

const empty = computed(() => !loading.value && rows.value.length === 0);
const canLoad = computed(() => Boolean(props.issueId));

function displayLabel(row: IssueLink): string {
  const title = (row.title || '').trim();
  if (title) return title;
  return hostnameFromUrl(row.url) || row.url;
}

async function load() {
  if (!canLoad.value) {
    rows.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data, error } = await fetchIssueLinks(props.issueId);
    if (error || !data) {
      window.$message?.error(error?.message || $t('page.issueLink.loadFailed'));
      return;
    }
    rows.value = data.rows || [];
  } finally {
    loading.value = false;
  }
}

async function onAdd() {
  const url = newUrl.value.trim();
  if (!url) {
    window.$message?.warning($t('page.issueLink.urlRequired'));
    return;
  }
  if (!isHttpUrl(url)) {
    window.$message?.warning($t('page.issueLink.httpOnly'));
    return;
  }
  saving.value = true;
  try {
    const { error } = await createIssueLink(props.issueId, {
      url,
      title: newTitle.value.trim() || undefined
    });
    if (error) {
      window.$message?.error(error.message || $t('page.issueLink.addFailed'));
      return;
    }
    window.$message?.success($t('page.issueLink.added'));
    newUrl.value = '';
    newTitle.value = '';
    await load();
  } finally {
    saving.value = false;
  }
}

function startEdit(row: IssueLink) {
  editingId.value = row.id;
  editUrl.value = row.url;
  editTitle.value = row.title || '';
}

function cancelEdit() {
  editingId.value = null;
  editUrl.value = '';
  editTitle.value = '';
}

async function saveEdit(row: IssueLink) {
  const url = editUrl.value.trim();
  if (!url || !isHttpUrl(url)) {
    window.$message?.warning($t('page.issueLink.httpOnly'));
    return;
  }
  saving.value = true;
  try {
    const { error } = await patchIssueLink(props.issueId, row.id, {
      url,
      title: editTitle.value.trim() || ''
    });
    if (error) {
      window.$message?.error(error.message || $t('page.issueLink.updateFailed'));
      return;
    }
    window.$message?.success($t('page.issueLink.updated'));
    cancelEdit();
    await load();
  } finally {
    saving.value = false;
  }
}

async function onDelete(row: IssueLink) {
  const { error } = await deleteIssueLink(props.issueId, row.id);
  if (error) {
    window.$message?.error(error.message || $t('page.issueLink.deleteFailed'));
    return;
  }
  window.$message?.success($t('page.issueLink.deleted'));
  await load();
}

watch(
  () => props.issueId,
  () => {
    load();
  }
);

onMounted(load);
</script>

<template>
  <NCard size="small" :title="$t('page.issueLink.title')" class="issue-links-panel">
    <NSpin :show="loading">
      <NEmpty v-if="empty" :description="$t('page.issueLink.empty')" size="small" />
      <div v-else class="link-list">
        <div v-for="row in rows" :key="row.id" class="link-row">
          <template v-if="editingId === row.id">
            <NSpace vertical :size="6" style="width: 100%">
              <NInput v-model:value="editUrl" size="small" placeholder="https://…" />
              <NInput v-model:value="editTitle" size="small" :placeholder="$t('page.issueLink.titleOptional')" />
              <NSpace :size="6">
                <NButton size="tiny" type="primary" :loading="saving" @click="saveEdit(row)">
                  {{ $t('page.issueLink.save') }}
                </NButton>
                <NButton size="tiny" quaternary @click="cancelEdit">{{ $t('common.cancel') }}</NButton>
              </NSpace>
            </NSpace>
          </template>
          <template v-else>
            <div class="link-main">
              <a :href="row.url" target="_blank" rel="noopener noreferrer" class="link-anchor">
                {{ displayLabel(row) }}
              </a>
              <NText v-if="row.title" depth="3" class="link-host">
                {{ hostnameFromUrl(row.url) }}
              </NText>
            </div>
            <NSpace :size="4">
              <NButton size="tiny" quaternary @click="startEdit(row)">{{ $t('common.edit') }}</NButton>
              <NButton size="tiny" quaternary type="error" @click="onDelete(row)">{{ $t('common.delete') }}</NButton>
            </NSpace>
          </template>
        </div>
      </div>

      <div class="link-add mt-8px">
        <NSpace vertical :size="6" style="width: 100%">
          <NInput v-model:value="newUrl" size="small" placeholder="https://…" />
          <NInput v-model:value="newTitle" size="small" :placeholder="$t('page.issueLink.titleOptional')" />
          <NButton size="small" type="primary" :loading="saving" @click="onAdd">
            {{ $t('page.issueLink.addLink') }}
          </NButton>
        </NSpace>
      </div>
    </NSpin>
  </NCard>
</template>

<style scoped>
.issue-links-panel :deep(.n-card__content) {
  padding-top: 8px;
}
.link-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.link-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.link-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 2px;
}
.link-anchor {
  color: var(--n-text-color);
  text-decoration: none;
  word-break: break-all;
}
.link-anchor:hover {
  color: var(--n-primary-color);
  text-decoration: underline;
}
.link-host {
  font-size: 12px;
}
.link-add {
  border-top: 1px solid var(--n-border-color);
  padding-top: 8px;
}
</style>
