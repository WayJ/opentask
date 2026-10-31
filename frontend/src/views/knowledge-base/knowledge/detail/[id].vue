<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Vditor from 'vditor';
import { useLoading } from '@sa/hooks';
import { fetchKnowledgeDetail, likeKnowledge } from '@/service/api/knowledge';
import 'vditor/dist/index.css';

defineOptions({
  name: 'KnowledgeDetail'
});

const router = useRouter();
const route = useRoute();
const { loading, startLoading, endLoading } = useLoading();

// 知识文档数据
const knowledge = ref<Api.Knowledge.Knowledge | null>(null);

// 点赞中
const liking = ref(false);

// 获取知识详情
async function getKnowledgeDetail() {
  startLoading();
  const id = route.params.id as string;
  const { data } = await fetchKnowledgeDetail(id);

  if (data) {
    knowledge.value = data;

    // 渲染 Markdown
    Vditor.preview(document.getElementById('preview')!, data.content, {
      mode: 'light',
      cdn: 'https://unpkg.com/vditor@3.9.9'
    });
  }

  endLoading();
}

// 编辑
function handleEdit() {
  router.push({
    name: 'knowledge-base_knowledge_edit',
    params: {
      id: route.params.id
    }
  });
}

// 点赞
async function handleLike() {
  if (!knowledge.value) return;

  liking.value = true;
  const { error } = await likeKnowledge(knowledge.value.id);

  if (!error && knowledge.value) {
    knowledge.value.likeCount += 1;
    window.$message?.success('点赞成功');
  }

  liking.value = false;
}

// 返回列表
function handleBack() {
  router.back();
}

onMounted(() => {
  getKnowledgeDetail();
});
</script>

<template>
  <div v-loading="loading" class="h-full overflow-y-auto bg-white p-4">
    <NPageHeader :title="knowledge?.title || '知识文档'" @back="handleBack">
      <template #extra>
        <NSpace>
          <NButton secondary @click="handleEdit">
            <template #icon>
              <icon-mdi:pencil class="text-icon" />
            </template>
            编辑
          </NButton>
        </NSpace>
      </template>
      <template #footer>
        <NSpace>
          <NTag size="small" type="info">
            <template #icon>
              <icon-mdi:eye class="text-icon" />
            </template>
            {{ knowledge?.viewCount || 0 }}
          </NTag>
          <NTag size="small" type="warning">
            <template #icon>
              <icon-mdi:heart class="text-icon" />
            </template>
            {{ knowledge?.likeCount || 0 }}
          </NTag>
          <NTag size="small" :type="knowledge?.status === 'published' ? 'success' : 'default'">
            {{ knowledge?.status === 'draft' ? '草稿' : knowledge?.status === 'published' ? '已发布' : '已归档' }}
          </NTag>
        </NSpace>
      </template>
    </NPageHeader>

    <div class="mx-auto max-w-4xl pt-4">
      <!-- 元信息 -->
      <NCard class="mb-4" :bordered="false">
        <NDescriptions :column="2">
          <NDescriptionsItem label="创建时间">
            {{ knowledge?.createdAt }}
          </NDescriptionsItem>
          <NDescriptionsItem label="更新时间">
            {{ knowledge?.updatedAt }}
          </NDescriptionsItem>
          <NDescriptionsItem label="版本">v{{ knowledge?.version || 1 }}</NDescriptionsItem>
          <NDescriptionsItem label="可见性">
            {{ knowledge?.visibility === 'public' ? '公开' : knowledge?.visibility === 'internal' ? '内部' : '私密' }}
          </NDescriptionsItem>
        </NDescriptions>
        <NSpace class="mt-3">
          <NButton :loading="liking" secondary strong @click="handleLike">
            <template #icon>
              <icon-mdi:heart class="text-icon" />
            </template>
            点赞
          </NButton>
        </NSpace>
      </NCard>

      <!-- 内容预览 -->
      <NCard :bordered="false">
        <div id="preview" class="vditor-reset" />
      </NCard>
    </div>
  </div>
</template>

<style scoped>
#preview :deep(.vditor-reset) {
  color: #1f2937;
  background-color: #fff;
  padding: 0;
}

#preview :deep(h1),
#preview :deep(h2),
#preview :deep(h3),
#preview :deep(h4),
#preview :deep(h5),
#preview :deep(h6) {
  color: var(--color-text-primary);
  font-weight: 600;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}

#preview :deep(p) {
  margin: 1em 0;
  line-height: 1.7;
}

#preview :deep(code) {
  background-color: #f3f4f6;
  padding: 0.2em 0.4em;
  border-radius: 0.25rem;
  font-size: 0.9em;
}

#preview :deep(pre) {
  background-color: #1f2937;
  color: #f9fafb;
  padding: 1em;
  border-radius: 0.5rem;
  overflow-x: auto;
  margin: 1em 0;
}

#preview :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: inherit;
}

#preview :deep(blockquote) {
  border-left: 4px solid var(--color-primary);
  padding-left: 1em;
  margin: 1em 0;
  color: var(--color-text-secondary);
}

#preview :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
}

#preview :deep(table th),
#preview :deep(table td) {
  border: 1px solid var(--color-border-subtle);
  padding: 0.5em 1em;
}

#preview :deep(table th) {
  background-color: #f9fafb;
  font-weight: 600;
}

#preview :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 0.5rem;
  margin: 1em 0;
}

#preview :deep(a) {
  color: var(--color-primary);
  text-decoration: none;
}

#preview :deep(a:hover) {
  text-decoration: underline;
}
</style>
