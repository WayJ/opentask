<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import {
  type DataTableColumns,
  NButton,
  NCard,
  NDataTable,
  NInput,
  NInputNumber,
  NModal,
  NSpace,
  NTag,
  NText
} from 'naive-ui';
import {
  type IssueTemplatePayload,
  type IssueTemplateRow,
  fetchCreateIssueTemplate,
  fetchDeleteIssueTemplate,
  fetchIssueTemplates,
  fetchSeedIssueTemplates,
  fetchUpdateIssueTemplate
} from '@/service/api/issue-templates';
import {
  issueTemplateSeedConfirmText,
  issueTemplateSourceLabel
} from '@/utils/issueTemplateSourceLabel';
import { $t } from '@/locales';

defineOptions({ name: 'WorkspaceIssueTemplatesPage' });

const loading = ref(false);
const seeding = ref(false);
const rows = ref<IssueTemplateRow[]>([]);
const showEditor = ref(false);
const saving = ref(false);
const editingId = ref<string | null>(null);

const form = reactive({
  name: '',
  description: '',
  icon: 'i-carbon-document',
  sortOrder: 0,
  title: '',
  body: '',
  type: 'bug',
  priority: 'medium'
});

const isEdit = computed(() => Boolean(editingId.value));

function buildPayload(): IssueTemplatePayload {
  return {
    title: form.title || undefined,
    description: form.body || undefined,
    type: form.type || undefined,
    priority: form.priority || undefined
  };
}

function formBody() {
  return {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    icon: form.icon || undefined,
    sortOrder: form.sortOrder,
    payload: buildPayload()
  };
}

const columns: DataTableColumns<IssueTemplateRow> = [
  {
    title: '名称',
    key: 'name',
    render: row =>
      h('div', { class: 'flex items-center gap-8px' }, [
        h('span', { class: row.icon || 'i-carbon-document' }),
        h(NText, { strong: true }, { default: () => row.name })
      ])
  },
  {
    title: '来源',
    key: 'source',
    width: 100,
    render: row =>
      h(
        NTag,
        { size: 'small', type: row.source === 'seed' ? 'info' : 'success', bordered: false },
        { default: () => issueTemplateSourceLabel(row.source) }
      )
  },
  {
    title: '类型/优先级',
    key: 'payload',
    render: row => `${row.payload?.type || '-'} / ${row.payload?.priority || '-'}`
  },
  {
    title: '排序',
    key: 'sortOrder',
    width: 80
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: row =>
      h(
        NSpace,
        { size: 8 },
        {
          default: () => [
            h(NButton, { size: 'tiny', tertiary: true, onClick: () => openEdit(row) }, { default: () => '编辑' }),
            h(
              NButton,
              { size: 'tiny', tertiary: true, type: 'error', onClick: () => removeRow(row.id) },
              { default: () => '删除' }
            )
          ]
        }
      )
  }
];

function resetForm() {
  form.name = '';
  form.description = '';
  form.icon = 'i-carbon-document';
  form.sortOrder = 0;
  form.title = '';
  form.body = '';
  form.type = 'bug';
  form.priority = 'medium';
  editingId.value = null;
}

function openCreate() {
  resetForm();
  showEditor.value = true;
}

function openEdit(row: IssueTemplateRow) {
  editingId.value = row.id;
  form.name = row.name;
  form.description = row.description || '';
  form.icon = row.icon || 'i-carbon-document';
  form.sortOrder = row.sortOrder ?? 0;
  form.title = row.payload?.title || '';
  form.body = row.payload?.description || '';
  form.type = row.payload?.type || 'bug';
  form.priority = row.payload?.priority || 'medium';
  showEditor.value = true;
}

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchIssueTemplates();
    if (error) {
      window.$message?.error?.(error.message || '加载失败');
      rows.value = [];
      return;
    }
    rows.value = data?.rows || [];
  } finally {
    loading.value = false;
  }
}

async function persistCreate() {
  const { error } = await fetchCreateIssueTemplate(formBody());
  if (error) {
    window.$message?.error?.(error.message || '创建失败');
    return false;
  }
  window.$message?.success?.('模板已创建');
  return true;
}

async function persistUpdate(id: string) {
  const { error } = await fetchUpdateIssueTemplate(id, formBody());
  if (error) {
    window.$message?.error?.(error.message || '更新失败');
    return false;
  }
  window.$message?.success?.('模板已更新');
  return true;
}

async function save() {
  if (!form.name.trim()) {
    window.$message?.warning?.('请输入模板名称');
    return;
  }
  saving.value = true;
  try {
    const ok = editingId.value ? await persistUpdate(editingId.value) : await persistCreate();
    if (!ok) return;
    showEditor.value = false;
    resetForm();
    await load();
  } finally {
    saving.value = false;
  }
}

async function removeRow(id: string) {
  const { error } = await fetchDeleteIssueTemplate(id);
  if (error) {
    window.$message?.error?.(error.message || '删除失败');
    return;
  }
  window.$message?.success?.('已删除');
  await load();
}


async function seedBuiltin() {
  const ok = window.confirm(issueTemplateSeedConfirmText());
  if (!ok) return;
  seeding.value = true;
  try {
    const { error } = await fetchSeedIssueTemplates();
    if (error) {
      window.$message?.error?.(error.message || '恢复内置失败');
      return;
    }
    window.$message?.success?.('内置模板已就绪');
    await load();
  } finally {
    seeding.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="h-full flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
    <NCard :title="$t('route.workspace_issue-templates')" :bordered="false" class="card-wrapper sm:flex-1-hidden">
      <NSpace vertical :size="16">
        <NSpace justify="space-between">
          <NText depth="3">工作区问题创建模板（与 PGE Prompt 无关）</NText>
          <NSpace>
            <NButton :loading="seeding" @click="seedBuiltin">恢复内置</NButton>
            <NButton type="primary" @click="openCreate">新建模板</NButton>
          </NSpace>
        </NSpace>
        <NDataTable :columns="columns" :data="rows" :loading="loading" :bordered="false" size="small" />
      </NSpace>
    </NCard>

    <NModal
      v-model:show="showEditor"
      preset="card"
      :title="isEdit ? '编辑模板' : '新建模板'"
      class="issue-template-editor-modal"
      :mask-closable="false"
    >
      <NSpace vertical :size="12">
        <NInput v-model:value="form.name" placeholder="名称（必填）" />
        <NInput v-model:value="form.description" placeholder="简介" />
        <NInput v-model:value="form.icon" placeholder="图标 class，如 i-carbon-bug" />
        <NInputNumber v-model:value="form.sortOrder" placeholder="排序" class="w-full" />
        <NInput v-model:value="form.title" placeholder="默认标题（可选）" />
        <NInput v-model:value="form.body" type="textarea" :rows="4" placeholder="默认描述 / Markdown 骨架" />
        <NInput v-model:value="form.type" placeholder="默认类型 bug/feature/…" />
        <NInput v-model:value="form.priority" placeholder="默认优先级 low/medium/high/…" />
        <NSpace justify="end">
          <NButton @click="showEditor = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="save">保存</NButton>
        </NSpace>
      </NSpace>
    </NModal>
  </div>
</template>

<style scoped>
.issue-template-editor-modal {
  width: min(560px, 92vw);
}
.w-full {
  width: 100%;
}
</style>
