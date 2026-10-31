<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import type { Ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Vditor from 'vditor';
import { createKnowledge, fetchKnowledgeDetail, updateKnowledge } from '@/service/api/knowledge';
import { fetchKnowledgeBaseList } from '@/service/api/knowledge-base';
import { fetchKnowledgeCategoryTree } from '@/service/api/knowledge-category';
import { $t } from '@/locales';
import 'vditor/dist/index.css';

defineOptions({
  name: 'KnowledgeEdit'
});

const router = useRouter();
const route = useRoute();

// 表单数据
const formRef = ref();
const formData = ref({
  title: '',
  knowledgeBaseId: '',
  categoryId: null as number | null,
  content: '',
  status: 'draft',
  visibility: 'internal'
});

// 知识库列表
const knowledgeBases: Ref<Api.Knowledge.KnowledgeBase[]> = ref([]);

// 分类树
const categoryTree = ref([]);

// 编辑器实例
const vditor: Ref<Vditor | undefined> = ref();

// 提交中
const submitting = ref(false);

// 是否为编辑模式
const isEdit = computed(() => Boolean(route.params.id));

// 获取知识库列表
async function getKnowledgeBases() {
  const { data } = await fetchKnowledgeBaseList({
    current: 1,
    pageSize: 100
  });

  if (data?.rows) {
    knowledgeBases.value = data.rows;
    // 如果是新建且有预设知识库ID
    if (!isEdit.value && route.query.knowledgeBaseId) {
      formData.value.knowledgeBaseId = route.query.knowledgeBaseId as string;
    }
  }
}

// 获取分类树
async function getCategoryTree() {
  const { data } = await fetchKnowledgeCategoryTree();

  if (data) {
    categoryTree.value = data;
  }
}

// 获取知识详情
async function getKnowledgeDetail() {
  const id = route.params.id as string;
  const { data } = await fetchKnowledgeDetail(id);

  if (data) {
    formData.value = {
      title: data.title,
      knowledgeBaseId: data.knowledgeBaseId,
      categoryId: data.categoryId,
      content: data.content,
      status: data.status,
      visibility: data.visibility
    };

    // 初始化编辑器内容
    if (vditor.value) {
      vditor.value.setValue(data.content);
    }
  }
}

// 初始化编辑器
function initEditor() {
  vditor.value = new Vditor('vditor', {
    height: 600,
    placeholder: '请输入内容...',
    theme: 'classic',
    counter: {
      enable: true
    },
    cache: {
      enable: true
    },
    mode: 'wysiwyg',
    toolbar: [
      'headings',
      'bold',
      'italic',
      'strike',
      '|',
      'list',
      'ordered-list',
      'check',
      '|',
      'code',
      'inline-code',
      '|',
      'link',
      'table',
      '|',
      'export',
      'preview',
      'fullscreen'
    ],
    after: () => {
      if (isEdit.value && formData.value.content) {
        vditor.value?.setValue(formData.value.content);
      }
    }
  });
}

// 保存
async function handleSave(status: string = 'draft') {
  try {
    await formRef.value?.validate();

    submitting.value = true;
    formData.value.status = status;
    formData.value.content = vditor.value?.getValue() || '';

    if (isEdit.value) {
      const { error } = await updateKnowledge(route.params.id as string, formData.value);
      if (!error) {
        window.$message?.success($t('common.updateSuccess'));
        router.back();
      }
    } else {
      const { data, error } = await createKnowledge(formData.value);
      if (!error && data) {
        window.$message?.success($t('common.addSuccess'));
        router.replace({
          name: 'knowledge_edit',
          params: { id: data.id }
        });
      }
    }
  } catch (e) {
    console.error(e);
  } finally {
    submitting.value = false;
  }
}

// 取消
function handleCancel() {
  router.back();
}

onMounted(async () => {
  await getKnowledgeBases();
  await getCategoryTree();

  if (isEdit.value) {
    await getKnowledgeDetail();
  }

  initEditor();
});
</script>

<template>
  <div class="h-full overflow-y-auto bg-white p-4">
    <NPageHeader title="编辑知识文档" @back="handleCancel" />

    <div class="mx-auto max-w-5xl pt-4">
      <NForm ref="formRef" :model="formData" label-placement="top" require-mark-placement="right-hanging">
        <!-- 标题 -->
        <NFormItem label="标题" path="title">
          <NInput v-model:value="formData.title" placeholder="请输入标题" @keyup.enter.ctrl="handleSave" />
        </NFormItem>

        <!-- 知识库和分类 -->
        <NGrid :cols="2" :x-gap="12">
          <NFormItem label="知识库" path="knowledgeBaseId">
            <NSelect
              v-model:value="formData.knowledgeBaseId"
              :options="knowledgeBases.map(kb => ({ label: kb.name, value: kb.id }))"
              placeholder="选择知识库"
              :disabled="isEdit"
            />
          </NFormItem>

          <NFormItem label="分类" path="categoryId">
            <NTreeSelect
              v-model:value="formData.categoryId"
              :options="categoryTree"
              label-field="name"
              key-field="id"
              children-field="children"
              placeholder="选择分类"
              clearable
            />
          </NFormItem>
        </NGrid>

        <!-- 状态和可见性 -->
        <NGrid :cols="2" :x-gap="12">
          <NFormItem label="状态" path="status">
            <NRadioGroup v-model:value="formData.status">
              <NRadioButton value="draft">草稿</NRadioButton>
              <NRadioButton value="published">发布</NRadioButton>
              <NRadioButton value="archived">归档</NRadioButton>
            </NRadioGroup>
          </NFormItem>

          <NFormItem label="可见性" path="visibility">
            <NRadioGroup v-model:value="formData.visibility">
              <NRadioButton value="public">公开</NRadioButton>
              <NRadioButton value="internal">内部</NRadioButton>
              <NRadioButton value="private">私密</NRadioButton>
            </NRadioGroup>
          </NFormItem>
        </NGrid>

        <!-- Markdown 编辑器 -->
        <NFormItem label="内容" path="content">
          <div id="vditor" class="w-full" />
        </NFormItem>

        <!-- 操作按钮 -->
        <NFormItem>
          <NSpace>
            <NButton type="primary" :loading="submitting" @click="handleSave('draft')">
              <template #icon>
                <icon-mdi:content-save class="text-icon" />
              </template>
              保存草稿
            </NButton>
            <NButton type="success" :loading="submitting" @click="handleSave('published')">
              <template #icon>
                <icon-mdi:publish class="text-icon" />
              </template>
              发布
            </NButton>
            <NButton @click="handleCancel">
              <template #icon>
                <icon-mdi:cancel class="text-icon" />
              </template>
              取消
            </NButton>
          </NSpace>
        </NFormItem>
      </NForm>
    </div>
  </div>
</template>

<style scoped>
#vditor :deep(.vditor) {
  border: 1px solid var(--color-border-subtle);
  border-radius: 0.375rem;
}
</style>
