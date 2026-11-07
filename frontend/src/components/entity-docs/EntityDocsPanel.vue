<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  type EntityDocParentType,
  type EntityDocumentRow,
  fetchCreateEntityDocument,
  fetchDeleteEntityDocument,
  fetchEntityDocuments,
  fetchUpdateEntityDocument
} from '@/service/api';

const props = defineProps<{
  parentType: EntityDocParentType;
  parentId: string;
}>();

defineOptions({ name: 'EntityDocsPanel' });

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const saving = ref(false);
const rows = ref<EntityDocumentRow[]>([]);
const editorOpen = ref(false);
const editingId = ref<string | null>(null);
const form = reactive({ title: '', bodyMd: '' });

const empty = computed(() => !loading.value && rows.value.length === 0);
const canLoad = computed(() => Boolean(props.parentId && props.parentType));

async function load() {
  if (!canLoad.value) {
    rows.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data, error } = await fetchEntityDocuments(props.parentType, props.parentId);
    if (error || !data) {
      window.$message?.error(error?.message || '加载文档失败');
      return;
    }
    rows.value = data.rows || [];
    openDocFromQuery();
  } finally {
    loading.value = false;
  }
}

function openDocFromQuery() {
  const docId = String(route.query.doc || '');
  if (!docId) return;
  const hit = rows.value.find(r => r.id === docId);
  if (hit) openEdit(hit);
}

function openCreate() {
  editingId.value = null;
  form.title = '';
  form.bodyMd = '';
  editorOpen.value = true;
}

function openEdit(row: EntityDocumentRow) {
  editingId.value = row.id;
  form.title = row.title;
  form.bodyMd = row.bodyMd || '';
  editorOpen.value = true;
}

async function onSave() {
  const title = form.title.trim();
  if (!title) {
    window.$message?.warning('请输入标题');
    return;
  }
  if (!canLoad.value) return;
  saving.value = true;
  try {
    if (editingId.value) {
      const { error } = await fetchUpdateEntityDocument(editingId.value, {
        title,
        bodyMd: form.bodyMd
      });
      if (error) {
        window.$message?.error(error.message || '保存失败');
        return;
      }
    } else {
      const { error } = await fetchCreateEntityDocument({
        parentType: props.parentType,
        parentId: props.parentId,
        title,
        bodyMd: form.bodyMd
      });
      if (error) {
        window.$message?.error(error.message || '创建失败');
        return;
      }
    }
    window.$message?.success('已保存');
    editorOpen.value = false;
    await load();
  } finally {
    saving.value = false;
  }
}

async function onDelete(row: EntityDocumentRow) {
  const { error } = await fetchDeleteEntityDocument(row.id);
  if (error) {
    window.$message?.error(error.message || '删除失败');
    return;
  }
  window.$message?.success('已删除');
  await load();
}

function openKnowledgeBase() {
  router.push({ path: '/knowledge-base' });
}

watch(
  () => [props.parentType, props.parentId],
  () => {
    load();
  }
);

onMounted(load);
</script>

<template>
  <NCard :bordered="false" title="文档 Docs" size="small">
    <template #header-extra>
      <div class="flex gap-8px">
        <NButton size="small" quaternary @click="openKnowledgeBase">在知识库中打开</NButton>
        <NButton size="small" type="primary" :disabled="!canLoad" @click="openCreate">新建短文档</NButton>
      </div>
    </template>

    <p class="mb-12px text-12px text-gray-500">
      轻量 Markdown 备注（问题 / 项目 / 举措）。完整文档请用知识库。不引导遗留需求 / PGE。
    </p>

    <NSpin :show="loading">
      <NEmpty v-if="empty" description="暂无短文档">
        <template #extra>
          <NSpace>
            <NButton size="small" type="primary" @click="openCreate">新建</NButton>
            <NButton size="small" @click="openKnowledgeBase">打开知识库</NButton>
          </NSpace>
        </template>
      </NEmpty>
      <div v-else class="flex-col gap-8px">
        <div
          v-for="row in rows"
          :key="row.id"
          class="flex items-start justify-between gap-12px rounded-6px bg-gray-50 px-12px py-10px dark:bg-dark-600"
        >
          <div class="min-w-0 flex-1">
            <div class="truncate font-500">{{ row.title }}</div>
            <div class="mt-4px max-h-48px overflow-hidden whitespace-pre-wrap text-12px text-gray-500">
              {{ row.bodyMd || '（空正文）' }}
            </div>
          </div>
          <div class="flex shrink-0 gap-6px">
            <NButton size="tiny" @click="openEdit(row)">编辑</NButton>
            <NButton size="tiny" type="error" secondary @click="onDelete(row)">删除</NButton>
          </div>
        </div>
      </div>
    </NSpin>

    <NModal v-model:show="editorOpen" preset="card" :title="editingId ? '编辑文档' : '新建短文档'" class="w-560px">
      <NForm label-placement="left" label-width="72">
        <NFormItem label="标题" required>
          <NInput v-model:value="form.title" maxlength="200" />
        </NFormItem>
        <NFormItem label="正文">
          <NInput v-model:value="form.bodyMd" type="textarea" :rows="8" placeholder="Markdown 短文…" />
        </NFormItem>
      </NForm>
      <template #footer>
        <div class="flex justify-end gap-8px">
          <NButton @click="editorOpen = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="onSave">保存</NButton>
        </div>
      </template>
    </NModal>
  </NCard>
</template>
