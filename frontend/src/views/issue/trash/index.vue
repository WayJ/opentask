<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { NButton, NCard, NDataTable, NEmpty, NPagination, NSpace, NTag } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { getIssuePriorityTagType, getIssueStatusTagType } from '@/constants/issue';
import { issueApi } from '@/service/api/issue';
import { restoreSuccessMessage, trashEmptyHint } from '@/utils/issueTrashMeta';
import type { Api } from '@/typings/api';

defineOptions({ name: 'IssueTrash' });

const router = useRouter();
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

const columns: DataTableColumns<Api.Issue.Issue> = [
  {
    title: '编号',
    key: 'issue_code',
    width: 120,
    render: row =>
      h(
        NButton,
        { text: true, type: 'primary', onClick: () => openDetail(row) },
        { default: () => row.issue_code || (row as any).issueCode }
      )
  },
  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: row => h(NTag, { type: getIssueStatusTagType(row.status), size: 'small' }, { default: () => row.status })
  },
  {
    title: '优先级',
    key: 'priority',
    width: 100,
    render: row =>
      h(NTag, { type: getIssuePriorityTagType(row.priority), size: 'small' }, { default: () => row.priority })
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 180,
    render: row => (row as any).updated_at || (row as any).updatedAt || '—'
  },
  {
    title: '操作',
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
        { default: () => '恢复' }
      )
  }
];

onMounted(loadTrash);
</script>

<template>
  <div class="issue-trash-page">
    <NCard title="回收站" :bordered="false">
      <template #header-extra>
        <NSpace>
          <NButton secondary @click="router.push('/issue/list')">返回列表</NButton>
          <NButton secondary :loading="loading" @click="loadTrash">刷新</NButton>
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
      <NEmpty v-else :description="trashEmptyHint()" class="py-12" />

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
