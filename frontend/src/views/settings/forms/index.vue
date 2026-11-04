<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import {
  type DataTableColumns,
  NButton,
  NCard,
  NInput,
  NSpace,
  NSwitch,
  NText
} from 'naive-ui';
import {
  type FormFieldDef,
  type IssueFormRow,
  buildPublicUrl,
  ensureTitleField,
  fetchCreateForm,
  fetchDeleteForm,
  fetchForms,
  fetchRegenerateFormToken,
  fetchUpdateForm
} from '@/service/api/forms';

defineOptions({ name: 'SettingsFormsPage' });

const loading = ref(false);
const rows = ref<IssueFormRow[]>([]);
const creating = ref(false);
const form = reactive({
  name: '',
  slug: '',
  description: '',
  fieldsJson: JSON.stringify(
    [
      { key: 'title', type: 'title', label: '标题', required: true },
      { key: 'description', type: 'description', label: '描述' },
      { key: 'priority', type: 'priority', label: '优先级' }
    ],
    null,
    2
  )
});

const columns: DataTableColumns<IssueFormRow> = [
  {
    title: '名称',
    key: 'name',
    render: row =>
      h('div', [
        h('div', { style: 'font-weight:500' }, row.name),
        h(NText, { depth: 3, style: 'font-size:12px' }, { default: () => row.slug || '—' })
      ])
  },
  {
    title: '公开链接',
    key: 'publicPath',
    render: row =>
      h(
        NButton,
        {
          text: true,
          type: 'primary',
          size: 'tiny',
          onClick: () => copyLink(row)
        },
        { default: () => row.publicPath || `/f/${row.token}` }
      )
  },
  {
    title: '启用',
    key: 'enabled',
    width: 90,
    render: row =>
      h(NSwitch, {
        value: row.enabled,
        size: 'small',
        onUpdateValue: (v: boolean) => toggle(row, v)
      })
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render: row =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(
            NButton,
            { size: 'tiny', tertiary: true, onClick: () => copyLink(row) },
            { default: () => '复制链接' }
          ),
          h(
            NButton,
            { size: 'tiny', tertiary: true, onClick: () => regen(row.id) },
            { default: () => '重生 token' }
          ),
          h(
            NButton,
            { size: 'tiny', tertiary: true, type: 'error', onClick: () => removeForm(row.id) },
            { default: () => '删除' }
          )
        ]
      })
  }
];

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchForms();
    if (error) {
      window.$message?.error?.(error.message || '加载失败');
      return;
    }
    rows.value = data?.rows || [];
  } finally {
    loading.value = false;
  }
}

function parseFields(): FormFieldDef[] | null {
  try {
    const parsed = JSON.parse(form.fieldsJson);
    if (!Array.isArray(parsed)) throw new Error('fields 须为数组');
    return ensureTitleField(parsed);
  } catch (e: any) {
    window.$message?.error?.(e?.message || 'fields JSON 无效');
    return null;
  }
}

async function createForm() {
  if (!form.name.trim()) {
    window.$message?.warning?.('请填写名称');
    return;
  }
  const fields = parseFields();
  if (!fields) return;
  creating.value = true;
  try {
    const { data, error } = await fetchCreateForm({
      name: form.name.trim(),
      slug: form.slug.trim() || undefined,
      description: form.description.trim() || undefined,
      fields
    });
    if (error) {
      window.$message?.error?.(error.message || '创建失败');
      return;
    }
    window.$message?.success?.(`已创建 ${data?.publicPath || ''}`);
    form.name = '';
    form.slug = '';
    form.description = '';
    await load();
  } finally {
    creating.value = false;
  }
}

async function toggle(row: IssueFormRow, enabled: boolean) {
  const prev = row.enabled;
  row.enabled = enabled;
  const { error } = await fetchUpdateForm(row.id, { enabled });
  if (error) {
    row.enabled = prev;
    window.$message?.error?.(error.message || '更新失败');
  }
}

async function regen(id: string) {
  const { data, error } = await fetchRegenerateFormToken(id);
  if (error) {
    window.$message?.error?.(error.message || '重生失败');
    return;
  }
  window.$message?.success?.(`新 token: ${data?.token?.slice(0, 8)}…`);
  await load();
}

async function removeForm(id: string) {
  const { error } = await fetchDeleteForm(id);
  if (error) {
    window.$message?.error?.(error.message || '删除失败');
    return;
  }
  window.$message?.success?.('已删除');
  await load();
}

async function copyLink(row: IssueFormRow) {
  const url = buildPublicUrl(row.publicPath || row.token);
  try {
    await navigator.clipboard.writeText(url);
    window.$message?.success?.('已复制公开链接');
  } catch {
    window.$message?.info?.(url);
  }
}

onMounted(load);
</script>

<template>
  <div class="p-4">
    <NCard title="公开 Issue 表单" :bordered="false">
      <template #header-extra>
        <NText depth="3">分享链接，无需登录即可创建 Issue</NText>
      </template>

      <NCard size="small" title="新建" class="mb-4">
        <NSpace vertical>
          <NInput v-model:value="form.name" placeholder="名称" />
          <NInput v-model:value="form.slug" placeholder="slug（可选，小写）" />
          <NInput v-model:value="form.description" type="textarea" placeholder="说明（公开页展示）" :rows="2" />
          <NInput v-model:value="form.fieldsJson" type="textarea" placeholder="fields JSON" :rows="8" />
          <NButton type="primary" :loading="creating" @click="createForm">创建</NButton>
        </NSpace>
      </NCard>

      <NDataTable :columns="columns" :data="rows" :loading="loading" :bordered="false" size="small" />
      <div v-if="!loading && !rows.length" class="py-8 text-center opacity-60">
        尚无表单。创建一个并把公开链接发给外部提报人。
      </div>
    </NCard>
  </div>
</template>
