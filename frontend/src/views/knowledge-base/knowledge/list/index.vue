<script setup lang="ts">
import { onMounted, ref } from 'vue';
import type { Ref } from 'vue';
import { useRouter } from 'vue-router';
import { useBoolean, useLoading } from '@sa/hooks';
import { deleteKnowledge, fetchKnowledgeList } from '@/service/api/knowledge';
import { fetchKnowledgeBaseList } from '@/service/api/knowledge-base';
import { $t } from '@/locales';

defineOptions({
  name: 'KnowledgeList'
});

const router = useRouter();
const { loading, startLoading, endLoading } = useLoading();
const { bool: empty, setBool: setEmpty } = useBoolean();

// 知识库列表
const knowledgeBases: Ref<Api.Knowledge.KnowledgeBase[]> = ref([]);
const selectedKnowledgeBaseId = ref<string>('');

// 知识文档列表
const knowledges: Ref<Api.Knowledge.Knowledge[]> = ref([]);

// 分页
const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
});

// 搜索参数
const searchParams = ref({
  keyword: '',
  status: '',
  categoryId: null as number | null
});

// 获取知识库列表
async function getKnowledgeBases() {
  const { data } = await fetchKnowledgeBaseList({
    current: 1,
    pageSize: 100
  });

  if (data?.rows) {
    knowledgeBases.value = data.rows;
  }
}

// 获取知识文档列表
async function getKnowledgeList() {
  startLoading();
  const { data } = await fetchKnowledgeList({
    knowledgeBaseId: selectedKnowledgeBaseId.value || undefined,
    keyword: searchParams.value.keyword || undefined,
    status: searchParams.value.status || undefined,
    categoryId: searchParams.value.categoryId || undefined,
    current: pagination.value.current,
    pageSize: pagination.value.pageSize
  });

  if (data) {
    knowledges.value = data.rows || [];
    pagination.value.total = data.total || 0;
    setEmpty(knowledges.value.length === 0);
  }

  endLoading();
}

// 搜索
function handleSearch() {
  pagination.value.current = 1;
  getKnowledgeList();
}

// 重置
function handleReset() {
  searchParams.value = {
    keyword: '',
    status: '',
    categoryId: null
  };
  pagination.value.current = 1;
  getKnowledgeList();
}

// 分页变化
function handlePageChange(page: number) {
  pagination.value.current = page;
  getKnowledgeList();
}

// 创建知识文档
function handleCreate() {
  router.push({
    name: 'knowledge-base_knowledge_edit',
    query: {
      knowledgeBaseId: selectedKnowledgeBaseId.value
    }
  });
}

// 编辑知识文档
function handleEdit(id: string) {
  router.push({
    name: 'knowledge-base_knowledge_edit',
    params: {
      id
    }
  });
}

// 查看知识文档
function handleView(id: string) {
  router.push({
    name: 'knowledge-base_knowledge_detail',
    params: {
      id
    }
  });
}

// 删除知识文档
async function handleDelete(id: string) {
  const { error } = await deleteKnowledge(id);

  if (!error) {
    window.$message?.success($t('common.deleteSuccess'));
    getKnowledgeList();
  }
}

onMounted(() => {
  getKnowledgeBases();
  getKnowledgeList();
});
</script>

<template>
  <div class="h-full overflow-y-auto bg-white p-4">
    <!-- 页面标题 -->
    <div class="mb-4 flex items-center justify-between">
      <NPageHeader title="知识文档" @back="router.back">
        <template #subtitle>管理和查看知识文档</template>
      </NPageHeader>
      <NButton type="primary" @click="handleCreate">
        <template #icon>
          <icon-ic-round-plus class="text-icon" />
        </template>
        新建知识
      </NButton>
    </div>

    <!-- 搜索栏 -->
    <NCard class="mb-4" :bordered="false">
      <NSpace vertical>
        <NSpace>
          <NInput
            v-model:value="searchParams.keyword"
            placeholder="搜索标题或内容"
            clearable
            @keyup.enter="handleSearch"
          />
          <NSelect
            v-model:value="selectedKnowledgeBaseId"
            :options="knowledgeBases.map(kb => ({ label: kb.name, value: kb.id }))"
            placeholder="选择知识库"
            clearable
            @update:value="handleSearch"
          />
          <NSelect
            v-model:value="searchParams.status"
            :options="[
              { label: '草稿', value: 'draft' },
              { label: '已发布', value: 'published' },
              { label: '已归档', value: 'archived' }
            ]"
            placeholder="选择状态"
            clearable
            @update:value="handleSearch"
          />
          <NButton type="primary" @click="handleSearch">
            <template #icon>
              <icon-mdi-search class="text-icon" />
            </template>
            查询
          </NButton>
          <NButton @click="handleReset">
            <template #icon>
              <icon-mdi-refresh class="text-icon" />
            </template>
            重置
          </NButton>
        </NSpace>
      </NSpace>
    </NCard>

    <!-- 知识文档列表 -->
    <NCard :bordered="false" :loading="loading">
      <NEmpty v-if="empty" description="暂无数据" class="h-300px" />
      <div v-else class="space-y-3">
        <NCard v-for="item in knowledges" :key="item.id" hoverable class="cursor-pointer" @click="handleView(item.id)">
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <h3 class="mb-2 text-lg font-semibold">{{ item.title }}</h3>
              <p class="line-clamp-2 text-sm text-gray-500">{{ item.content }}</p>
              <NSpace class="mt-2">
                <NTag size="small" :type="item.status === 'published' ? 'success' : 'default'">
                  {{ item.status === 'draft' ? '草稿' : item.status === 'published' ? '已发布' : '已归档' }}
                </NTag>
                <NTag size="small" type="info">浏览 {{ item.viewCount }}</NTag>
                <NTag size="small" type="warning">点赞 {{ item.likeCount }}</NTag>
              </NSpace>
            </div>
            <NSpace>
              <NButton size="small" @click.stop="handleEdit(item.id)">
                <template #icon>
                  <icon-mdi:pencil class="text-icon" />
                </template>
                编辑
              </NButton>
              <NPopconfirm @positive-click="handleDelete(item.id)">
                <template #trigger>
                  <NButton size="small" type="error">
                    <template #icon>
                      <icon-mdi:delete class="text-icon" />
                    </template>
                    删除
                  </NButton>
                </template>
                确定删除该知识文档吗？
              </NPopconfirm>
            </NSpace>
          </div>
        </NCard>
      </div>

      <!-- 分页 -->
      <div v-if="!empty" class="mt-4 flex justify-end">
        <NPagination
          v-model:page="pagination.current"
          :page-count="Math.ceil(pagination.total / pagination.pageSize)"
          :page-size="pagination.pageSize"
          show-quick-jumper
          @update:page="handlePageChange"
        />
      </div>
    </NCard>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
