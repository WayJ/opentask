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
  type ProjectTemplateRow,
  fetchCreateProjectTemplate,
  fetchDeleteProjectTemplate,
  fetchProjectTemplates,
  fetchUpdateProjectTemplate
} from '@/service/api/project-templates';
import { validateMilestonePayload } from '@/utils/projectTemplate';

defineOptions({ name: 'WorkspaceProjectTemplatesPage' });

const loading = ref(false);
const rows = ref<ProjectTemplateRow[]>([]);
const showEditor = ref(false);
const saving = ref(false);
const editingId = ref<string | null>(null);

const form = reactive({
  name: '',
  description: '',
  icon: 'i-carbon-folder',
  sortOrder: 0,
  payloadDescription: '',
  milestonesJson: '[]'
});

const isEdit = computed(() => Boolean(editingId.value));

function parseMilestones() {
  try {
    const parsed = JSON.parse(form.milestonesJson || '[]');
    if (!Array.isArray(parsed)) return { error: 'milestones must be a JSON array' as string, milestones: [] as any[] };
    const err = validateMilestonePayload(parsed);
    if (err) return { error: err, milestones: [] as any[] };
    return { error: null as string | null, milestones: parsed };
  } catch {
    return { error: 'invalid JSON', milestones: [] as any[] };
  }
}

function formBody() {
  const { error, milestones } = parseMilestones();
  if (error) throw new Error(error);
  return {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    icon: form.icon || undefined,
    sortOrder: form.sortOrder,
    payload: {
      description: form.payloadDescription.trim() || undefined,
      milestones
    }
  };
}

const columns: DataTableColumns<ProjectTemplateRow> = [
  {
    title: '名称',
    key: 'name',
    render: row =>
      h('div', { class: 'flex items-center gap-8px' }, [
        h('span', { class: row.icon || 'i-carbon-folder' }),
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
        { size: 'small', type: row.source === 'builtin' || row.source === 'seed' ? 'info' : 'success', bordered: false },
        { default: () => (row.source === 'custom' ? '自定义' : row.source) }
      )
  },
  {
    title: '里程碑数',
    key: 'payload',
    width: 100,
    render: row => String(row.payload?.milestones?.length ?? 0)
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
  form.icon = 'i-carbon-folder';
  form.sortOrder = 0;
  form.payloadDescription = '';
  form.milestonesJson = JSON.stringify(
    [
      { name: 'Kickoff', targetOffsetDays: 0 },
      { name: 'Beta', targetOffsetDays: 30 }
    ],
    null,
    2
  );
  editingId.value = null;
}

function openCreate() {
  resetForm();
  showEditor.value = true;
}

function openEdit(row: ProjectTemplateRow) {
  editingId.value = row.id;
  form.name = row.name;
  form.description = row.description || '';
  form.icon = row.icon || 'i-carbon-folder';
  form.sortOrder = row.sortOrder ?? 0;
  form.payloadDescription = row.payload?.description || '';
  form.milestonesJson = JSON.stringify(row.payload?.milestones || [], null, 2);
  showEditor.value = true;
}

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchProjectTemplates();
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

async function save() {
  if (!form.name.trim()) {
    window.$message?.warning?.('请输入模板名称');
    return;
  }
  saving.value = true;
  try {
    let body;
    try {
      body = formBody();
    } catch (e: any) {
      window.$message?.warning?.(e?.message || 'payload 无效');
      return;
    }
    const res = editingId.value
      ? await fetchUpdateProjectTemplate(editingId.value, body)
      : await fetchCreateProjectTemplate(body);
    if (res.error) {
      window.$message?.error?.(res.error.message || '保存失败');
      return;
    }
    window.$message?.success?.(editingId.value ? '模板已更新' : '模板已创建');
    showEditor.value = false;
    resetForm();
    await load();
  } finally {
    saving.value = false;
  }
}

async function removeRow(id: string) {
  const { error } = await fetchDeleteProjectTemplate(id);
  if (error) {
    window.$message?.error?.(error.message || '删除失败');
    return;
  }
  window.$message?.success?.('已删除');
  await load();
}

onMounted(load);
</script>

<template>
  <div class="h-full flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
    <NCard title="Project 模板" :bordered="false" class="card-wrapper sm:flex-1-hidden">
      <NSpace vertical :size="16">
        <NSpace justify="space-between">
          <NText depth="3">工作区 Project 创建模板（仅种子里程碑，不复制 Issues）</NText>
          <NButton type="primary" @click="openCreate">新建模板</NButton>
        </NSpace>
        <NDataTable :columns="columns" :data="rows" :loading="loading" :bordered="false" size="small" />
      </NSpace>
    </NCard>

    <NModal
      v-model:show="showEditor"
      preset="card"
      :title="isEdit ? '编辑 Project 模板' : '新建 Project 模板'"
      class="project-template-editor-modal"
      :mask-closable="false"
    >
      <NSpace vertical :size="12">
        <NInput v-model:value="form.name" placeholder="名称（必填）" />
        <NInput v-model:value="form.description" placeholder="简介" />
        <NInput v-model:value="form.icon" placeholder="图标 class" />
        <NInputNumber v-model:value="form.sortOrder" placeholder="排序" class="w-full" />
        <NInput v-model:value="form.payloadDescription" placeholder="应用到项目的默认描述" />
        <NText depth="3">Milestones JSON（name / targetOffsetDays / position）</NText>
        <NInput v-model:value="form.milestonesJson" type="textarea" :rows="10" />
        <NSpace justify="end">
          <NButton @click="showEditor = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="save">保存</NButton>
        </NSpace>
      </NSpace>
    </NModal>
  </div>
</template>

<style scoped>
.project-template-editor-modal {
  width: min(640px, 92vw);
}
.w-full {
  width: 100%;
}
</style>
