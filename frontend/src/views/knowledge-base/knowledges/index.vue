<script setup lang="ts">
/* eslint-disable @typescript-eslint/no-use-before-define */
import { h, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { NButton, NDataTable, NInput, NSpace, NTag, NText, NTooltip, useMessage } from 'naive-ui';
import { deleteKnowledge, fetchKnowledgeList } from '@/service/api/knowledge';
import { fetchKnowledgeBaseDetail } from '@/service/api/knowledge-base';
import type { Api } from '@/typings/api';
import KnowledgeDialog from './components/KnowledgeDialog.vue';

const message = useMessage();
const route = useRoute();
const router = useRouter();

// 从路由获取知识库ID
const knowledgeBaseId = ref((route.params.knowledgeBaseId as string) || (route.query.knowledgeBaseId as string) || '');

// 知识库信息（用于判断是否有 Git 仓库）
const knowledgeBase = ref<Api.Knowledge.KnowledgeBase | null>(null);

// 数据状态
const loading = ref(false);
const knowledges = ref<Api.Knowledge.Knowledge[]>([]);
const searchKeyword = ref('');
const statusFilter = ref<Api.Knowledge.KnowledgeStatus | null>(null);
const visibilityFilter = ref<Api.Knowledge.KnowledgeVisibility | null>(null);

// 对话框
const dialogVisible = ref(false);
const currentKnowledge = ref<Api.Knowledge.Knowledge | null>(null);

// 格式化日期
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN');
};

// 状态选项
const statusOptions = [
  { label: '全部', value: null },
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
  { label: '已归档', value: 'archived' }
];

// 可见性选项
const visibilityOptions = [
  { label: '全部', value: null },
  { label: '公开', value: 'public' },
  { label: '私有', value: 'private' }
];

// 编辑
const handleEdit = (row: Api.Knowledge.Knowledge) => {
  currentKnowledge.value = row;
  dialogVisible.value = true;
};

// Git 编辑
const handleGitEdit = (row: Api.Knowledge.Knowledge) => {
  if (!knowledgeBase.value?.repositoryUrl) {
    message.warning('该知识库未配置 Git 仓库');
    return;
  }

  router.push({
    name: 'knowledge-base_knowledge_edit_git',
    query: {
      kbId: knowledgeBaseId.value,
      docId: row.id,
      title: row.title
    }
  });
};

// 删除
const handleDelete = async (row: Api.Knowledge.Knowledge) => {
  const d = window.dialog;
  if (!d) {
    message.warning('浏览器不支持对话框');
    return;
  }

  const confirmed = d.confirm(`确定要删除知识文档"${row.title}"吗？`);
  if (!confirmed) return;

  try {
    await deleteKnowledge(row.id);
    message.success('删除成功');
    await loadKnowledgesData();
  } catch (error) {
    message.error('删除失败');
    // eslint-disable-next-line no-console
    console.error(error);
  }
};

// 加载知识库信息
const loadKnowledgeBase = async () => {
  if (!knowledgeBaseId.value) return;

  try {
    const { data } = await fetchKnowledgeBaseDetail(knowledgeBaseId.value);
    knowledgeBase.value = data;
  } catch (error) {
    console.error('加载知识库信息失败:', error);
  }
};

// 分页配置
const paginationConfig = ref({
  pageSize: 20,
  page: 1,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page: number) => {
    paginationConfig.value.page = page;
    loadKnowledgesData();
  },
  onUpdatePageSize: (pageSize: number) => {
    paginationConfig.value.pageSize = pageSize;
    paginationConfig.value.page = 1;
    loadKnowledgesData();
  }
});

// 加载知识文档列表
const loadKnowledgesData = async () => {
  loading.value = true;
  try {
    const { data } = await fetchKnowledgeList({
      current: paginationConfig.value.page,
      pageSize: paginationConfig.value.pageSize,
      keyword: searchKeyword.value || undefined,
      status: statusFilter.value || undefined,
      visibility: visibilityFilter.value || undefined,
      knowledgeBaseId: knowledgeBaseId.value || undefined
    });

    knowledges.value = data.rows;
  } catch (error) {
    message.error('加载知识文档失败');
    // eslint-disable-next-line no-console
    console.error(error);
  } finally {
    loading.value = false;
  }
};

// 表格列配置
const columns = [
  {
    title: '标题',
    key: 'title',
    minWidth: 300,
    render: (row: Api.Knowledge.Knowledge) => {
      return h('div', { class: 'kb-title-cell' }, [
        h('div', { class: 'kb-title' }, row.title),
        row.summary ? h('div', { class: 'kb-summary' }, row.summary) : null
      ]);
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    align: 'center',
    render: (row: Api.Knowledge.Knowledge) => {
      const statusMap = {
        draft: { type: 'default' as const, text: '草稿' },
        published: { type: 'success' as const, text: '已发布' },
        archived: { type: 'info' as const, text: '已归档' }
      };
      const { type, text } = statusMap[row.status];
      return h(NTag, { type, size: 'small' }, text);
    }
  },
  {
    title: '可见性',
    key: 'visibility',
    width: 100,
    align: 'center',
    render: (row: Api.Knowledge.Knowledge) => {
      return h(
        NTag,
        {
          type: row.visibility === 'public' ? 'success' : 'warning',
          size: 'small'
        },
        row.visibility === 'public' ? '公开' : '私有'
      );
    }
  },
  {
    title: '版本',
    key: 'version',
    width: 100,
    align: 'center',
    render: (row: Api.Knowledge.Knowledge) => {
      return h(NText, {}, `v${row.version}`);
    }
  },
  {
    title: '创建时间',
    key: 'createdAt',
    width: 180,
    render: (row: Api.Knowledge.Knowledge) => {
      return h(NText, {}, formatDate(row.createdAt));
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 280,
    render: (row: Api.Knowledge.Knowledge) => {
      return h(
        NSpace,
        {},
        {
          default: () => [
            // 普通编辑按钮
            h(
              NButton,
              {
                text: true,
                type: 'primary',
                onClick: () => handleEdit(row)
              },
              { default: () => '编辑' }
            ),
            // Git 编辑按钮（仅当知识库配置了 Git 仓库时显示）
            knowledgeBase.value?.repositoryUrl
              ? h(
                  NTooltip,
                  {},
                  {
                    trigger: () =>
                      h(
                        NButton,
                        {
                          text: true,
                          type: 'info',
                          onClick: () => handleGitEdit(row)
                        },
                        { default: () => 'Git编辑' }
                      ),
                    default: () => '使用 Monaco Editor + Git 进行高级编辑'
                  }
                )
              : null,
            // 删除按钮
            h(
              NButton,
              {
                text: true,
                type: 'error',
                onClick: () => handleDelete(row)
              },
              { default: () => '删除' }
            )
          ]
        }
      );
    }
  }
];

// 搜索
const handleSearch = () => {
  paginationConfig.value.page = 1;
  loadKnowledges();
};

// 创建
const handleCreate = () => {
  currentKnowledge.value = null;
  dialogVisible.value = true;
};

// 对话框成功回调
const handleDialogSuccess = () => {
  loadKnowledges();
};

// 初始化
onMounted(async () => {
  await loadKnowledgeBase();
  await loadKnowledgesData();
});
</script>

<template>
  <div class="knowledge-list">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="title-section">
        <h1>知识文档</h1>
        <p class="description">知识库的知识内容管理</p>
      </div>
      <NButton type="primary" @click="handleCreate">
        <template #icon>
          <span class="i-carbon-add" />
        </template>
        创建知识
      </NButton>
    </div>

    <!-- 搜索和筛选 -->
    <div class="filter-section">
      <NInput
        v-model:value="searchKeyword"
        placeholder="搜索知识标题"
        clearable
        style="width: 300px"
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <span class="i-carbon-search" />
        </template>
      </NInput>
      <NSelect
        v-model:value="statusFilter"
        placeholder="状态筛选"
        clearable
        style="width: 150px"
        :options="statusOptions"
        @update:value="handleSearch"
      />
      <NSelect
        v-model:value="visibilityFilter"
        placeholder="可见性"
        clearable
        style="width: 150px"
        :options="visibilityOptions"
        @update:value="handleSearch"
      />
      <NButton @click="handleSearch">查询</NButton>
    </div>

    <!-- 知识文档列表 -->
    <NDataTable
      :loading="loading"
      :columns="columns"
      :data="knowledges"
      :pagination="paginationConfig"
      :bordered="false"
      striped
    />

    <!-- 创建/编辑对话框 -->
    <KnowledgeDialog
      v-model:visible="dialogVisible"
      :knowledge="currentKnowledge"
      :knowledge-base-id="knowledgeBaseId"
      @success="handleDialogSuccess"
    />
  </div>
</template>

<style scoped lang="scss">
.knowledge-list {
  padding: 20px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .title-section {
      h1 {
        font-size: 24px;
        font-weight: 600;
        margin: 0 0 8px 0;
        color: #333;
      }

      .description {
        font-size: 14px;
        color: #666;
        margin: 0;
      }
    }
  }

  .filter-section {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    padding: 16px;
    background: #f5f5f5;
    border-radius: 4px;
  }

  .kb-title-cell {
    .kb-title {
      font-weight: 500;
      color: #333;
      margin-bottom: 4px;
    }

    .kb-summary {
      font-size: 12px;
      color: #999;
    }
  }
}
</style>
