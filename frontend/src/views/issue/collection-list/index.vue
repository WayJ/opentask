<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  NButton,
  NCard,
  NDataTable,
  NEmpty,
  NInput,
  NPagination,
  NPopconfirm,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  NText
} from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { CollectionStatus, STATUS_OPTIONS } from '@/constants/issue-collection';
import { issueCollectionApi } from '@/service/api';
import type { Api } from '@/typings/api';

defineOptions({
  name: 'IssueCollectionList'
});

const router = useRouter();

const collections = ref<Api.IssueCollection.CollectionResponse[]>([]);
const loading = ref(false);

// 分页状态
const pagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100]
});

// Filters
const filters = reactive({
  status: undefined as CollectionStatus | undefined,
  search: ''
});

// 状态选项
const statusOptions = STATUS_OPTIONS;

// 表格列定义
const columns: DataTableColumns<Api.IssueCollection.CollectionResponse> = [
  {
    title: '标题',
    key: 'title',
    width: 300,
    render: row => {
      return h(
        'a',
        {
          class: 'text-primary cursor-pointer hover:text-primary-hover',
          onClick: () => goToDetail(row.id)
        },
        row.title
      );
    }
  },
  {
    title: '创建人',
    key: 'creator',
    width: 120,
    render: row => {
      return h(
        NText,
        {},
        {
          default: () => row.creator?.jnpf_name || row.creator?.name || row.creator_id
        }
      );
    }
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render: row => {
      const date = new Date(row.created_at);
      return h(
        NText,
        {},
        {
          default: () =>
            date.toLocaleString('zh-CN', {
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit'
            })
        }
      );
    }
  },
  {
    title: '问题数',
    key: 'issue_count',
    width: 100,
    render: row => {
      return h(
        NText,
        {},
        {
          default: () => row.issue_ids?.length || 0
        }
      );
    }
  },
  {
    title: '完成进度',
    key: 'progress',
    width: 150,
    render: row => {
      if (!row.statistics || row.statistics.total === 0) {
        return h(NText, { depth: 3 }, { default: () => '暂无数据' });
      }
      const percentage = (row.statistics.completion_rate * 100).toFixed(0);
      return h(
        NSpace,
        { vertical: true, size: 2 },
        {
          default: () => [
            h(
              NText,
              {},
              {
                default: () => `${row.statistics.completed}/${row.statistics.total} (${percentage}%)`
              }
            ),
            h(
              'div',
              {
                class: 'w-full h-2 bg-gray-200 rounded-full overflow-hidden'
              },
              [
                h('div', {
                  class: 'h-full bg-primary rounded-full transition-all',
                  style: { width: `${percentage}%` }
                })
              ]
            )
          ]
        }
      );
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: row => {
      const statusMap = {
        [CollectionStatus.PENDING]: { type: 'default', text: '待拆解' },
        [CollectionStatus.IN_PROGRESS]: { type: 'warning', text: '拆解中' },
        [CollectionStatus.COMPLETED]: { type: 'success', text: '已完成' }
      };
      const status = statusMap[row.status];
      return h(NTag, { type: status.type as any }, { default: () => status.text });
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    fixed: 'right' as const,
    render: row => {
      return h(
        NSpace,
        {},
        {
          default: () => [
            h(
              NButton,
              {
                size: 'small',
                onClick: () => goToDetail(row.id)
              },
              { default: () => '查看' }
            ),
            h(
              NPopconfirm,
              {
                onPositiveClick: () => handleDelete(row.id)
              },
              {
                default: () => '确定删除此问题集吗？',
                trigger: () =>
                  h(
                    NButton,
                    {
                      size: 'small',
                      type: 'error'
                    },
                    { default: () => '删除' }
                  )
              }
            )
          ]
        }
      );
    }
  }
];

// 加载数据
async function loadCollections() {
  loading.value = true;
  try {
    const response = await issueCollectionApi.getCollections({
      page: pagination.page,
      page_size: pagination.pageSize,
      status: filters.status,
      search: filters.search || undefined,
      sort_by: 'created_at',
      sort_order: 'desc'
    });

    if (response.data?.rows) {
      collections.value = response.data.rows;
      pagination.itemCount = response.data.total;
    }
  } finally {
    loading.value = false;
  }
}

// 查看详情
function goToDetail(id: string) {
  router.push(`/issue/collection/${id}`);
}

// 删除问题集
async function handleDelete(id: string) {
  try {
    await issueCollectionApi.deleteCollection(id);
    window.$message?.success('删除成功');
    await loadCollections();
  } catch {
    window.$message?.error('删除失败');
  }
}

// 分页变化
function handlePageChange(page: number) {
  pagination.page = page;
  loadCollections();
}

function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize;
  pagination.page = 1;
  loadCollections();
}

// 筛选变化
function handleStatusChange(value: string | undefined) {
  filters.status = value as CollectionStatus | undefined;
  pagination.page = 1;
  loadCollections();
}

function handleSearch() {
  pagination.page = 1;
  loadCollections();
}

// 创建新问题集
function createCollection() {
  router.push('/issue/collection-create');
}

onMounted(() => {
  loadCollections();
});
</script>

<template>
  <div class="h-full overflow-hidden p-4">
    <NCard title="问题集" class="h-full rounded-16px shadow-sm">
      <template #header-extra>
        <NButton type="primary" @click="createCollection">
          <icon-ic-round-plus class="mr-1" />
          创建问题集
        </NButton>
      </template>

      <!-- 筛选栏 -->
      <NSpace vertical :size="16" class="mb-4">
        <NSpace :size="12">
          <NInput
            v-model:value="filters.search"
            placeholder="搜索标题或描述..."
            clearable
            style="width: 280px"
            @keyup.enter="handleSearch"
          >
            <template #suffix>
              <NButton text @click="handleSearch">
                <icon-mdi-search class="text-18px" />
              </NButton>
            </template>
          </NInput>
          <NSelect
            v-model:value="filters.status"
            placeholder="状态筛选"
            :options="statusOptions"
            clearable
            style="width: 150px"
            @update:value="handleStatusChange"
          />
        </NSpace>
      </NSpace>

      <!-- 数据表格 -->
      <NSpin :show="loading">
        <NDataTable
          v-if="collections.length > 0"
          :columns="columns"
          :data="collections"
          :scroll-x="1200"
          :bordered="false"
          striped
        />
        <NEmpty v-else description="暂无数据" class="py-12" />
      </NSpin>

      <!-- 分页 -->
      <NSpace v-if="collections.length > 0" justify="end" class="mt-4">
        <NPagination
          v-model:page="pagination.page"
          :page-count="Math.ceil(pagination.itemCount / pagination.pageSize)"
          :page-size="pagination.pageSize"
          :page-sizes="pagination.pageSizes"
          show-size-picker
          @update:page="handlePageChange"
          @update:page-size="handlePageSizeChange"
        />
      </NSpace>
    </NCard>
  </div>
</template>

<style scoped>
/* 进度条样式 */
.w-full {
  width: 100%;
}

.h-2 {
  height: 0.5rem;
}

.bg-gray-200 {
  background-color: rgb(229 231 235);
}

.bg-primary {
  background-color: rgb(14 165 233);
}

.rounded-full {
  border-radius: 9999px;
}

.overflow-hidden {
  overflow: hidden;
}

.transition-all {
  transition: all 0.3s ease;
}
</style>
