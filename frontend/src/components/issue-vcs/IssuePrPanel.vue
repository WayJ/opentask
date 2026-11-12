<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { NButton, NCard, NEmpty, NInput, NSpace, NSpin, NTag, NText } from 'naive-ui';
import { type IssueVcsLink, createIssueVcsLink, deleteIssueVcsLink, fetchIssueVcsLinks } from '@/service/api/issue-vcs';
import { $t } from '@/locales';

const props = defineProps<{
  issueId: string;
}>();

defineOptions({ name: 'IssuePrPanel' });

const loading = ref(false);
const saving = ref(false);
const rows = ref<IssueVcsLink[]>([]);
const prUrl = ref('');
const title = ref('');

const prRows = computed(() => rows.value.filter(r => r.kind === 'pull_request'));
const empty = computed(() => !loading.value && prRows.value.length === 0);
const canLoad = computed(() => Boolean(props.issueId));

function statusType(status: string): 'default' | 'info' | 'success' | 'warning' | 'error' {
  switch (status) {
    case 'merged':
      return 'success';
    case 'open':
      return 'info';
    case 'draft':
      return 'warning';
    case 'closed':
      return 'error';
    default:
      return 'default';
  }
}

async function load() {
  if (!canLoad.value) {
    rows.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data, error } = await fetchIssueVcsLinks(props.issueId);
    if (error || !data) {
      window.$message?.error(error?.message || $t('page.issuePr.loadFailed'));
      return;
    }
    rows.value = data.rows || [];
  } finally {
    loading.value = false;
  }
}

async function onAdd() {
  const url = prUrl.value.trim();
  if (!url) {
    window.$message?.warning($t('page.issuePr.urlRequired'));
    return;
  }
  saving.value = true;
  try {
    const { error } = await createIssueVcsLink(props.issueId, {
      kind: 'pull_request',
      prUrl: url,
      provider: 'github',
      status: 'open',
      title: title.value.trim() || undefined
    });
    if (error) {
      window.$message?.error(error.message || $t('page.issuePr.linkFailed'));
      return;
    }
    window.$message?.success($t('page.issuePr.linked'));
    prUrl.value = '';
    title.value = '';
    await load();
  } finally {
    saving.value = false;
  }
}

async function onUnlink(row: IssueVcsLink) {
  const { error } = await deleteIssueVcsLink(props.issueId, row.id);
  if (error) {
    window.$message?.error(error.message || $t('page.issuePr.unlinkFailed'));
    return;
  }
  window.$message?.success($t('page.issuePr.unlinked'));
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
  <NCard size="small" :title="$t('page.issuePr.title')" class="issue-pr-panel">
    <NSpin :show="loading">
      <NEmpty v-if="empty" :description="$t('page.issuePr.empty')" size="small" />
      <div v-else class="pr-list">
        <div v-for="row in prRows" :key="row.id" class="pr-row">
          <div class="pr-main">
            <NTag size="small" :type="statusType(row.status)" class="pr-status">
              {{ row.status }}
            </NTag>
            <a v-if="row.prUrl" :href="row.prUrl" target="_blank" rel="noopener noreferrer" class="pr-link">
              {{ row.title || row.prUrl }}
            </a>
            <NText v-else depth="3">{{ row.title || row.externalId || row.id }}</NText>
          </div>
          <NButton size="tiny" quaternary type="error" @click="onUnlink(row)">{{ $t('page.issuePr.unlink') }}</NButton>
        </div>
      </div>

      <div class="pr-add">
        <NSpace vertical :size="8" style="width: 100%">
          <!-- https://github.com/org/repo/pull/1 -->
          <NInput v-model:value="prUrl" size="small" :placeholder="$t('page.issuePr.urlPlaceholder')" />
          <NInput v-model:value="title" size="small" :placeholder="$t('page.issueLink.titleOptional')" />
          <NButton size="small" type="primary" :loading="saving" @click="onAdd">{{ $t('page.issuePr.add') }}</NButton>
        </NSpace>
      </div>
    </NSpin>
  </NCard>
</template>

<style scoped>
.issue-pr-panel {
  margin-top: 12px;
}
.pr-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}
.pr-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.pr-main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}
.pr-link {
  color: var(--n-primary-color, #18a058);
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pr-link:hover {
  text-decoration: underline;
}
.pr-add {
  border-top: 1px solid var(--n-border-color, #efeff5);
  padding-top: 12px;
}
</style>
