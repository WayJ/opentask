<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import type { DataTableColumns } from 'naive-ui';
import { NButton, NCard, NDataTable, NEmpty, NPagination, NSpace, NTag } from 'naive-ui';
import { useI18n } from 'vue-i18n';
import { getIssuePriorityTagType, getIssueStatusTagType } from '@/constants/issue';
import { issueApi } from '@/service/api/issue';
import { restoreSuccessMessage, trashEmptyHint } from '@/utils/issueTrashMeta';
import { $t } from '@/locales';
import { lookupLabel } from '@/locales/display-label';
import { useLabelTable } from '@/locales/use-label-table';
import type { Api } from '@/typings/api';

defineOptions({ name: 'IssueTrash' });

const router = useRouter();
const { locale } = useI18n();
const statusLabels = useLabelTable('page.issueStatus');
const priorityLabels = useLabelTable('page.issuePriority');
/* eslint-disable no-void -- derived chrome must read locale.value before $t */
const emptyHint = computed(() => {
  void locale.value;
  return trashEmptyHint();
});
/* eslint-enable no-void */
const loading = ref(false);
const restoringId = ref<string | null>(null);
const rows = ref<Api.Issue.Issue[]>([]);
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });

async function loadTrash() {
  loading.value = true;
  try {
    const response = await issueApi.listTrash({
      page: pagination.page,
      page_size: pagination.pageSize
    });
    const payload = (response as any)?.data ?? response;
    rows.value = (payload?.rows || []) as Api.Issue.Issue[];
    pagination.total = payload?.total ?? rows.value.length;
  } catch {
    window.$message?.error('加载回收站失败');
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

async function handleRestore(row: Api.Issue.Issue) {
  restoringId.value = row.id;
  try {
    await issueApi.restoreIssue(row.id);
    window.$message?.success(restoreSuccessMessage(row.issue_code || ''));
    await loadTrash();
  } catch {
    window.$message?.error('恢复失败（需要 member 权限）');
  } finally {
    restoringId.value = null;
  }
}

function openDetail(row: Api.Issue.Issue) {
  router.push({ path: '/issue/detail', query: { id: row.id, trash: '1' } });
}

/* eslint-disable no-void -- derived chrome must read locale.value before $t */
const columns = computed<DataTableColumns<Api.Issue.Issue>>(() => {
  void locale.value;
  return [
    {
      title: $t('page.issueTrash.key'),
      key: 'issue_code',
      width: 120,
      render: row =>
        h(
          NButton,
          { text: true, type: 'primary', onClick: () => openDetail(row) },
          { default: () => row.issue_code || (row as any).issueCode }
        )
    },
    { title: $t('page.issueTrash.issueTitle'), key: 'title', ellipsis: { tooltip: true } },
    {
      title: $t('page.issueTrash.status'),
      key: 'status',
      width: 100,
      render: row =>
        h(
          NTag,
          { type: getIssueStatusTagType(row.status), size: 'small' },
          { default: () => lookupLabel(statusLabels.value, row.status) }
        )
    },
    {
      title: $t('page.issueTrash.priority'),
      key: 'priority',
      width: 100,
      render: row =>
        h(
          NTag,
          { type: getIssuePriorityTagType(row.priority), size: 'small' },
          { default: () => lookupLabel(priorityLabels.value, row.priority) }
        )
    },
    {
      title: $t('page.issueTrash.updatedAt'),
      key: 'updated_at',
      width: 180,
      render: row => (row as any).updated_at || (row as any).updatedAt || '—'
    },
    {
      title: $t('page.issueTrash.actions'),
      key: 'actions',
      width: 120,
      render: row =>
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            loading: restoringId.value === row.id,
            onClick: () => handleRestore(row)
          },
          { default: () => $t('page.issueTrash.restore') }
        )
    }
  ];
});
/* eslint-enable no-void */

onMounted(loadTrash);
</script>

<template>
  <div class="issue-trash-page">
    <NCard :title="$t('page.issueTrash.title')" :bordered="false">
      <template #header-extra>
        <NSpace>
          <NButton secondary @click="router.push('/issue/list')">{{ $t('page.issueTrash.backToList') }}</NButton>
          <NButton secondary :loading="loading" @click="loadTrash">{{ $t('page.issueTrash.refresh') }}</NButton>
        </NSpace>
      </template>

      <NDataTable
        v-if="rows.length || loading"
        :columns="columns"
        :data="rows"
        :loading="loading"
        :bordered="false"
        :single-line="false"
      />
      <NEmpty v-else :description="emptyHint" class="py-12" />

      <div v-if="pagination.total > pagination.pageSize" class="mt-4 flex justify-end">
        <NPagination
          v-model:page="pagination.page"
          :page-size="pagination.pageSize"
          :item-count="pagination.total"
          @update:page="
            p => {
              pagination.page = p;
              loadTrash();
            }
          "
        />
      </div>
    </NCard>
  </div>
</template>

<style scoped>
.issue-trash-page {
  padding: 16px;
}
</style>
