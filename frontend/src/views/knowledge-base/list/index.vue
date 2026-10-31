<script setup lang="ts">
/* eslint-disable @typescript-eslint/no-use-before-define */
import { h, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { NButton, NDataTable, NImage, NSpace, NTag, NText, useMessage } from 'naive-ui';
import { deleteKnowledgeBase, fetchKnowledgeBaseList } from '@/service/api/knowledge-base';
import type { Api } from '@/typings/api';
import KnowledgeBaseDialog from './components/KnowledgeBaseDialog.vue';
import ProjectAssociationDialog from './components/ProjectAssociationDialog.vue';

const message = useMessage();
const router = useRouter();

// 数据状态
const loading = ref(false);
const knowledgeBases = ref<Api.KnowledgeBase.KnowledgeBase[]>([]);
const searchKeyword = ref('');
const statusFilter = ref<Api.KnowledgeBase.KnowledgeBaseStatus | null>(null);
const dialogVisible = ref(false);
const currentKB = ref<Api.KnowledgeBase.KnowledgeBase | null>(null);
const projectDialogVisible = ref(false);
const total = ref(0);

// 状态选项
const statusOptions = [
  { label: '全部', value: null },
  { label: '活跃', value: 'active' },
  { label: '已归档', value: 'archived' }
];

// 分页配置
const paginationConfig = ref({
  pageSize: 20,
  page: 1,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page: number) => {
    paginationConfig.value.page = page;
    loadKnowledgeBases();
  },
  onUpdatePageSize: (pageSize: number) => {
    paginationConfig.value.pageSize = pageSize;
    paginationConfig.value.page = 1;
    loadKnowledgeBases();
  }
});

// 格式化日期
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN');
};

// 加载知识库列表
const loadKnowledgeBases = async () => {
  loading.value = true;
  try {
    const { data } = await fetchKnowledgeBaseList({
      current: paginationConfig.value.page,
      pageSize: paginationConfig.value.pageSize,
      keyword: searchKeyword.value || undefined,
      status: statusFilter.value || undefined
    });

    // API 返回的是 { data: { rows: [...], total: ... } }
    const data_response = data;

    // 转换字段名：后端返回蛇形命名，前端需要驼峰命名
    const rows = (data_response.rows || []).map((item: any) => ({
      id: item.id,
      name: item.name,
      description: item.description,
      icon: item.icon,
      repositoryUrl: item.repository_url,
      status: item.status,
      knowledgeCount: item.knowledge_count,
      createdAt: item.created_at,
      updatedAt: item.updated_at
    }));

    knowledgeBases.value = rows;
    total.value = data_response.total || 0;
  } catch (error) {
    message.error('加载知识库列表失败');
    // eslint-disable-next-line no-console
    console.error(error);
  } finally {
    loading.value = false;
  }
};

// 搜索
const handleSearch = () => {
  paginationConfig.value.page = 1;
  loadKnowledgeBases();
};

// 创建
const handleCreate = () => {
  currentKB.value = null;
  dialogVisible.value = true;
};

// 查看
const handleView = (row: Api.KnowledgeBase.KnowledgeBase) => {
  router.push({
    path: '/knowledge-base/knowledges',
    query: { knowledgeBaseId: row.id }
  });
};

// 编辑
const handleEdit = (row: Api.KnowledgeBase.KnowledgeBase) => {
  currentKB.value = row;
  dialogVisible.value = true;
};

// 删除
const handleDelete = async (row: Api.KnowledgeBase.KnowledgeBase) => {
  const d = window.dialog;
  if (!d) {
    message.warning('浏览器不支持对话框');
    return;
  }

  const confirmed = d.confirm(`确定要删除知识库"${row.name}"吗？删除后关联的知识文档也会被删除。`);
  if (!confirmed) return;

  try {
    await deleteKnowledgeBase(row.id);
    message.success('删除成功');
    loadKnowledgeBases();
  } catch (error) {
    message.error('删除失败');
    // eslint-disable-next-line no-console
    console.error(error);
  }
};

// 对话框成功回调
const handleDialogSuccess = () => {
  loadKnowledgeBases();
};

// 管理项目关联
const handleManageProjects = (row: Api.KnowledgeBase.KnowledgeBase) => {
  currentKB.value = row;
  projectDialogVisible.value = true;
};

// 项目关联成功回调
const handleProjectDialogSuccess = () => {
  // 刷新列表数据以更新知识数量
  loadKnowledgeBases();
};

// 表格列配置
const columns = [
  {
    title: '名称',
    key: 'name',
    minWidth: 300,
    render: (row: Api.KnowledgeBase.KnowledgeBase) => {
      return h('div', { class: 'kb-name-cell' }, [
        h(NImage, {
          width: 40,
          height: 40,
          src: row.icon || '',
          fallbackSrc: '',
          class: 'kb-icon'
        }),
        h('div', { class: 'kb-info' }, [
          h('div', { class: 'kb-name' }, row.name),
          h('div', { class: 'kb-desc' }, row.description || '暂无描述')
        ])
      ]);
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    align: 'center' as const,
    render: (row: Api.KnowledgeBase.KnowledgeBase) => {
      return h(
        NTag,
        {
          type: row.status === 'active' ? 'success' : 'default',
          size: 'small'
        },
        row.status === 'active' ? '活跃' : '已归档'
      );
    }
  },
  {
    title: '知识数量',
    key: 'knowledgeCount',
    width: 120,
    align: 'center' as const,
    render: (row: Api.KnowledgeBase.KnowledgeBase) => {
      return h(NText, {}, row.knowledgeCount.toString());
    }
  },
  {
    title: '创建时间',
    key: 'createdAt',
    width: 180,
    render: (row: Api.KnowledgeBase.KnowledgeBase) => {
      return h(NText, {}, formatDate(row.createdAt));
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row: Api.KnowledgeBase.KnowledgeBase) => {
      return h(
        NSpace,
        {},
        {
          default: () => [
            h(
              NButton,
              {
                text: true,
                type: 'primary',
                onClick: () => handleView(row)
              },
              '查看知识'
            ),
            h(
              NButton,
              {
                text: true,
                type: 'primary',
                onClick: () => handleEdit(row)
              },
              '编辑'
            ),
            h(
              NButton,
              {
                text: true,
                type: 'error',
                onClick: () => handleDelete(row)
              },
              '删除'
            ),
            h(
              NButton,
              {
                text: true,
                type: 'info',
                onClick: () => handleManageProjects(row)
              },
              '管理项目'
            )
          ]
        }
      );
    }
  }
];

// 初始化
onMounted(() => {
  loadKnowledgeBases();
});
</script>

<template>
  <div class="knowledge-base-list">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="title-section">
        <h1>知识库管理</h1>
        <p class="description">管理团队的知识积累和文档</p>
      </div>
      <NButton type="primary" @click="handleCreate">
        <template #icon>
          <span class="i-carbon-add" />
        </template>
        创建知识库
      </NButton>
    </div>

    <!-- 搜索和筛选 -->
    <div class="filter-section">
      <NInput
        v-model:value="searchKeyword"
        placeholder="搜索知识库名称"
        clearable
        class="search-input"
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
        class="status-select"
        :options="statusOptions"
        @update:value="handleSearch"
      />
      <NButton @click="handleSearch">查询</NButton>
    </div>

    <!-- 知识库列表 -->
    <NDataTable
      :loading="loading"
      :columns="columns"
      :data="knowledgeBases"
      :pagination="paginationConfig"
      :bordered="false"
      striped
    />

    <!-- 创建/编辑对话框 -->
    <KnowledgeBaseDialog v-model:visible="dialogVisible" :knowledge-base="currentKB" @success="handleDialogSuccess" />

    <!-- 项目关联对话框 -->
    <ProjectAssociationDialog
      v-model:visible="projectDialogVisible"
      :knowledge-base="currentKB"
      @success="handleProjectDialogSuccess"
    />
  </div>
</template>

<style scoped lang="scss">
.knowledge-base-list {
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

    .search-input {
      width: 300px;
    }

    .status-select {
      width: 150px;
    }
  }

  .kb-name-cell {
    display: flex;
    align-items: center;
    gap: 12px;

    .kb-icon {
      border-radius: 4px;
    }

    .kb-info {
      flex: 1;

      .kb-name {
        font-weight: 500;
        color: #333;
        margin-bottom: 4px;
      }

      .kb-desc {
        font-size: 12px;
        color: #999;
      }
    }
  }
}
</style>
