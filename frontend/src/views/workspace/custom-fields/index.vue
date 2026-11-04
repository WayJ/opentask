<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import {
  type DataTableColumns,
  NButton,
  NCard,
  NDataTable,
  NInput,
  NSelect,
  NSpace,
  NTag,
  NText
} from 'naive-ui';
import {
  type CustomFieldRow,
  type CustomFieldType,
  type FormulaResultType,
  fetchCreateCustomField,
  fetchCustomFields,
  fetchDeleteCustomField,
  fetchReorderCustomFields,
  fetchUpdateCustomField,
  fetchValidateFormula
} from '@/service/api/custom-fields';

defineOptions({ name: 'WorkspaceCustomFieldsPage' });

const loading = ref(false);
const rows = ref<CustomFieldRow[]>([]);
const creating = ref(false);
const validating = ref(false);
const form = reactive({
  name: '',
  key: '',
  type: 'text' as CustomFieldType,
  optionsText: '',
  formulaExpr: '',
  formulaResultType: 'number' as FormulaResultType
});

const typeOptions = [
  { label: 'text', value: 'text' },
  { label: 'number', value: 'number' },
  { label: 'boolean', value: 'boolean' },
  { label: 'date', value: 'date' },
  { label: 'single_select', value: 'single_select' },
  { label: 'multi_select', value: 'multi_select' },
  { label: '公式 formula', value: 'formula' }
];

const resultTypeOptions = [
  { label: 'number', value: 'number' },
  { label: 'boolean', value: 'boolean' },
  { label: 'text', value: 'text' },
  { label: 'date', value: 'date' }
];

const isSelect = computed(() => form.type === 'single_select' || form.type === 'multi_select');
const isFormula = computed(() => form.type === 'formula');

const columns: DataTableColumns<CustomFieldRow> = [
  { title: '名称', key: 'name' },
  {
    title: 'Key',
    key: 'key',
    render: row => h(NTag, { size: 'small', bordered: false }, { default: () => row.key })
  },
  { title: '类型', key: 'type', width: 120 },
  {
    title: '选项/公式',
    key: 'options',
    render: row => {
      if (row.type === 'formula') {
        return row.formulaExpr || '—';
      }
      return (row.options || []).map(o => o.label || o.value).join(', ') || '—';
    }
  },
  { title: '排序', key: 'position', width: 70 },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render: row =>
      h(
        NSpace,
        { size: 4 },
        {
          default: () => [
            h(NButton, { size: 'tiny', tertiary: true, onClick: () => move(row.id, -1) }, { default: () => '上移' }),
            h(NButton, { size: 'tiny', tertiary: true, onClick: () => move(row.id, 1) }, { default: () => '下移' }),
            h(
              NButton,
              {
                size: 'tiny',
                tertiary: true,
                type: 'warning',
                onClick: () => archiveField(row.id)
              },
              { default: () => '归档' }
            ),
            h(
              NButton,
              {
                size: 'tiny',
                tertiary: true,
                type: 'error',
                onClick: () => removeField(row.id)
              },
              { default: () => '删除' }
            )
          ]
        }
      )
  }
];

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchCustomFields();
    if (error) {
      window.$message?.error?.(error.message || '加载失败');
      return;
    }
    rows.value = data?.rows || [];
  } finally {
    loading.value = false;
  }
}

function parseOptions(text: string) {
  return text
    .split(/[\n,]/)
    .map(s => s.trim())
    .filter(Boolean)
    .map(s => {
      if (s.includes('=')) {
        const [value, label] = s.split('=', 2);
        return { value: value.trim(), label: (label || value).trim() };
      }
      return { value: s, label: s };
    });
}

async function validateExpr() {
  if (!form.formulaExpr.trim()) {
    window.$message?.warning?.('请输入公式表达式');
    return;
  }
  validating.value = true;
  try {
    const { data, error } = await fetchValidateFormula({
      formulaExpr: form.formulaExpr.trim(),
      formulaResultType: form.formulaResultType
    });
    if (error) {
      window.$message?.error?.(error.message || '校验失败');
      return;
    }
    if (data?.ok) {
      window.$message?.success?.(`校验通过 · deps: ${(data.dependencies || []).join(', ') || '—'}`);
    } else {
      window.$message?.error?.(data?.error || '公式无效');
    }
  } finally {
    validating.value = false;
  }
}

async function createField() {
  if (!form.name.trim()) {
    window.$message?.warning?.('请输入名称');
    return;
  }
  if (isSelect.value && !form.optionsText.trim()) {
    window.$message?.warning?.('select 类型需要 options');
    return;
  }
  if (isFormula.value && !form.formulaExpr.trim()) {
    window.$message?.warning?.('公式需要表达式');
    return;
  }
  creating.value = true;
  try {
    const { error } = await fetchCreateCustomField({
      name: form.name.trim(),
      type: form.type,
      key: form.key.trim() || undefined,
      options: isSelect.value ? parseOptions(form.optionsText) : undefined,
      formulaExpr: isFormula.value ? form.formulaExpr.trim() : undefined,
      formulaResultType: isFormula.value ? form.formulaResultType : undefined
    });
    if (error) {
      window.$message?.error?.(error.message || '创建失败');
      return;
    }
    form.name = '';
    form.key = '';
    form.optionsText = '';
    form.formulaExpr = '';
    form.formulaResultType = 'number';
    window.$message?.success?.('已创建');
    await load();
  } finally {
    creating.value = false;
  }
}

async function archiveField(id: string) {
  const { error } = await fetchUpdateCustomField(id, { archive: true });
  if (error) {
    window.$message?.error?.(error.message || '归档失败');
    return;
  }
  window.$message?.success?.('已归档');
  await load();
}

async function removeField(id: string) {
  const { error } = await fetchDeleteCustomField(id);
  if (error) {
    window.$message?.error?.(error.message || '删除失败（有取值请先归档）');
    return;
  }
  window.$message?.success?.('已删除');
  await load();
}

async function move(id: string, delta: number) {
  const ids = rows.value.map(r => r.id);
  const idx = ids.indexOf(id);
  const j = idx + delta;
  if (idx < 0 || j < 0 || j >= ids.length) return;
  const next = [...ids];
  const tmp = next[idx];
  next[idx] = next[j];
  next[j] = tmp;
  const { error } = await fetchReorderCustomFields(next);
  if (error) {
    window.$message?.error?.(error.message || '排序失败');
    return;
  }
  await load();
}

onMounted(load);
</script>

<template>
  <div class="h-full flex-col-stretch gap-12px overflow-hidden lt-sm:overflow-auto">
    <NCard title="自定义字段 Custom Fields" :bordered="false" class="card-wrapper sm:flex-1-hidden">
      <NSpace vertical :size="16">
        <NSpace align="center" :wrap="true">
          <NInput v-model:value="form.name" placeholder="名称" style="width: 160px" />
          <NInput v-model:value="form.key" placeholder="key（可选）" style="width: 140px" />
          <NSelect v-model:value="form.type" :options="typeOptions" style="width: 160px" />
          <NInput
            v-if="isSelect"
            v-model:value="form.optionsText"
            placeholder="选项：a,b 或 a=A（逗号/换行）"
            style="width: 260px"
          />
          <NSelect
            v-if="isFormula"
            v-model:value="form.formulaResultType"
            :options="resultTypeOptions"
            style="width: 120px"
          />
          <NButton type="primary" :loading="creating" @click="createField">创建字段</NButton>
        </NSpace>
        <template v-if="isFormula">
          <NInput
            v-model:value="form.formulaExpr"
            type="textarea"
            :rows="3"
            placeholder='表达式，如 IF(issue.priority == "urgent", 10, COALESCE(cf.weight, 0) * COALESCE(cf.impact, 0))'
          />
          <NSpace align="center">
            <NButton size="small" :loading="validating" @click="validateExpr">校验公式</NButton>
            <NText depth="3" style="font-size: 12px">
              可用：cf.&lt;key&gt;、issue.estimate_points|priority|status、days_until_due；函数
              IF/COALESCE/ABS/MIN/MAX/ROUND/LEN/LOWER/UPPER/DATE_DIFF。只读计算，不触发自动化。
            </NText>
          </NSpace>
        </template>
        <NDataTable :columns="columns" :data="rows" :loading="loading" :bordered="false" size="small" />
      </NSpace>
    </NCard>
  </div>
</template>
