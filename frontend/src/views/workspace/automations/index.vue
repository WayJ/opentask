<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from 'vue';
import {
  type DataTableColumns,
  NButton,
  NCard,
  NDataTable,
  NInput,
  NSelect,
  NSpace,
  NSwitch,
  NTag
} from 'naive-ui';
import {
  type AutomationRuleRow,
  type CustomFieldConditionOp,
  CF_CONDITION_OPS,
  fetchAutomations,
  fetchCreateAutomation,
  fetchDeleteAutomation,
  fetchDisableAutomation,
  fetchEnableAutomation,
  parseAutomationJson,
  summarizeAutomationRule,
  withCustomFieldCondition,
  withCustomFieldConditions,
  MAX_CUSTOM_FIELD_CONDITIONS
} from '@/service/api/automations';
import { type CustomFieldRow, fetchCustomFields } from '@/service/api/custom-fields';

defineOptions({ name: 'WorkspaceAutomationsPage' });

const loading = ref(false);
const rows = ref<AutomationRuleRow[]>([]);
const creating = ref(false);
const customFields = ref<CustomFieldRow[]>([]);

const form = reactive({
  name: '',
  triggerType: 'issue.created',
  actionType: 'set_priority',
  triggerConfigText: '',
  conditionText: '',
  actionConfigText: '{"priority":"high"}',
  // E33 CF helpers
  cfKey: null as string | null,
  cfOp: 'eq' as CustomFieldConditionOp,
  cfValue: '',
  actionCfKey: null as string | null,
  actionCfValue: '',
  // E36 CF-changed trigger + multi conditions
  triggerCfKey: null as string | null,
  triggerFrom: '',
  triggerTo: '',
  extraCfKey: null as string | null,
  extraCfOp: 'eq' as CustomFieldConditionOp,
  extraCfValue: ''
});

const triggerOptions = [
  { label: 'issue.created', value: 'issue.created' },
  { label: 'issue.status_changed', value: 'issue.status_changed' },
  { label: 'issue.assignee_changed', value: 'issue.assignee_changed' },
  { label: 'label_added', value: 'label_added' },
  { label: 'custom_field_changed', value: 'custom_field_changed' }
];

const actionOptions = [
  { label: 'set_status', value: 'set_status' },
  { label: 'set_assignee', value: 'set_assignee' },
  { label: 'add_label', value: 'add_label' },
  { label: 'set_priority', value: 'set_priority' },
  { label: 'add_comment', value: 'add_comment' },
  { label: 'set_custom_field', value: 'set_custom_field' }
];

const cfOptions = computed(() =>
  customFields.value.map(f => ({
    label: `${f.name} (${f.key})`,
    value: f.key
  }))
);

const cfValueNeeded = computed(() => form.cfOp !== 'is_set' && form.cfOp !== 'is_empty');

function syncTriggerConfigFromHelpers() {
  if (form.triggerType !== 'custom_field_changed') return;
  const cfg: Record<string, unknown> = {};
  if (form.triggerCfKey) cfg.field_key = form.triggerCfKey;
  const fr = (form.triggerFrom || '').trim();
  const to = (form.triggerTo || '').trim();
  if (fr) cfg.from = coerceHelperValue(fr);
  if (to) cfg.to = coerceHelperValue(to);
  form.triggerConfigText = Object.keys(cfg).length ? JSON.stringify(cfg) : '';
}

function syncConditionFromHelpers() {
  let base: Record<string, unknown> = {};
  try {
    if (form.conditionText.trim()) base = parseAutomationJson(form.conditionText);
  } catch {
    base = {};
  }
  const list: Array<{ key: string; op: CustomFieldConditionOp; value?: unknown }> = [];
  if (form.cfKey) {
    list.push({
      key: form.cfKey,
      op: form.cfOp,
      value: coerceHelperValue(form.cfValue)
    });
  }
  if (form.extraCfKey) {
    list.push({
      key: form.extraCfKey,
      op: form.extraCfOp,
      value: coerceHelperValue(form.extraCfValue)
    });
  }
  if (list.length > MAX_CUSTOM_FIELD_CONDITIONS) {
    window.$message?.error?.(`customFields 最多 ${MAX_CUSTOM_FIELD_CONDITIONS} 条`);
    return;
  }
  let next: Record<string, unknown> | null;
  if (list.length <= 1) {
    next = withCustomFieldCondition(base, list[0] || null);
  } else {
    // strip single keys then write array
    const cleaned = withCustomFieldCondition(base, null) || {};
    next = withCustomFieldConditions(cleaned, list);
  }
  form.conditionText = next ? JSON.stringify(next) : '';
}

function syncActionFromHelpers() {
  if (form.actionType !== 'set_custom_field') return;
  if (!form.actionCfKey) {
    form.actionConfigText = '{}';
    return;
  }
  form.actionConfigText = JSON.stringify({
    key: form.actionCfKey,
    value: coerceHelperValue(form.actionCfValue)
  });
}

function coerceHelperValue(raw: string): unknown {
  const t = (raw || '').trim();
  if (!t) return '';
  if (t === 'true') return true;
  if (t === 'false') return false;
  if (t.startsWith('[') || t.startsWith('{') || t.startsWith('"')) {
    try {
      return JSON.parse(t);
    } catch {
      return t;
    }
  }
  if (/^-?\d+(\.\d+)?$/.test(t)) return Number(t);
  return t;
}

watch(
  () => [form.triggerType, form.triggerCfKey, form.triggerFrom, form.triggerTo],
  () => syncTriggerConfigFromHelpers()
);
watch(
  () => [form.cfKey, form.cfOp, form.cfValue, form.extraCfKey, form.extraCfOp, form.extraCfValue],
  () => syncConditionFromHelpers()
);
watch(
  () => [form.actionType, form.actionCfKey, form.actionCfValue],
  () => syncActionFromHelpers()
);

const columns: DataTableColumns<AutomationRuleRow> = [
  { title: '名称', key: 'name' },
  {
    title: 'Trigger',
    key: 'triggerType',
    render: row => h(NTag, { size: 'small', bordered: false }, { default: () => row.triggerType })
  },
  {
    title: 'Action',
    key: 'actionType',
    render: row => h(NTag, { size: 'small', type: 'info', bordered: false }, { default: () => row.actionType })
  },
  {
    title: '摘要',
    key: 'summary',
    ellipsis: { tooltip: true },
    render: row => summarizeAutomationRule(row)
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
    width: 100,
    render: row =>
      h(
        NButton,
        { size: 'tiny', tertiary: true, type: 'error', onClick: () => removeRule(row.id) },
        { default: () => '删除' }
      )
  }
];

async function load() {
  loading.value = true;
  try {
    const [{ data, error }, cfRes] = await Promise.all([fetchAutomations(), fetchCustomFields()]);
    if (error) {
      window.$message?.error?.(error.message || '加载失败');
      return;
    }
    rows.value = data?.rows || [];
    if (!cfRes.error) {
      customFields.value = cfRes.data?.rows || [];
    }
  } finally {
    loading.value = false;
  }
}

async function createRule() {
  if (!form.name.trim()) {
    window.$message?.warning?.('请输入名称');
    return;
  }
  syncTriggerConfigFromHelpers();
  syncConditionFromHelpers();
  syncActionFromHelpers();
  let triggerConfig: Record<string, unknown> = {};
  let actionConfig: Record<string, unknown> = {};
  let condition: Record<string, unknown> | null = null;
  try {
    triggerConfig = parseAutomationJson(form.triggerConfigText);
    actionConfig = parseAutomationJson(form.actionConfigText);
    if (form.conditionText.trim()) {
      condition = parseAutomationJson(form.conditionText);
    }
  } catch (e: any) {
    window.$message?.error?.(e?.message || 'JSON 无效');
    return;
  }
  creating.value = true;
  try {
    const { error } = await fetchCreateAutomation({
      name: form.name.trim(),
      triggerType: form.triggerType,
      actionType: form.actionType,
      triggerConfig,
      actionConfig,
      condition
    });
    if (error) {
      window.$message?.error?.(error.message || '创建失败');
      return;
    }
    form.name = '';
    form.triggerConfigText = '';
    form.conditionText = '';
    form.cfKey = null;
    form.cfValue = '';
    form.extraCfKey = null;
    form.extraCfValue = '';
    form.triggerCfKey = null;
    form.triggerFrom = '';
    form.triggerTo = '';
    form.actionCfKey = null;
    form.actionCfValue = '';
    window.$message?.success?.('已创建');
    await load();
  } finally {
    creating.value = false;
  }
}

async function toggle(row: AutomationRuleRow, enabled: boolean) {
  const fn = enabled ? fetchEnableAutomation : fetchDisableAutomation;
  const { error } = await fn(row.id);
  if (error) {
    window.$message?.error?.(error.message || '切换失败');
    return;
  }
  row.enabled = enabled;
}

async function removeRule(id: string) {
  const { error } = await fetchDeleteAutomation(id);
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
  <div class="h-full flex-col-stretch gap-12px overflow-hidden lt-sm:overflow-auto">
    <NCard title="自动化 Automations" :bordered="false" class="card-wrapper sm:flex-1-hidden">
      <NSpace vertical :size="16">
        <NSpace align="center" :wrap="true">
          <NInput v-model:value="form.name" placeholder="规则名称" style="width: 180px" />
          <NSelect v-model:value="form.triggerType" :options="triggerOptions" style="width: 200px" />
          <template v-if="form.triggerType === 'custom_field_changed'">
            <NSelect
              v-model:value="form.triggerCfKey"
              :options="cfOptions"
              clearable
              placeholder="字段(可选)"
              style="width: 180px"
            />
            <NInput v-model:value="form.triggerFrom" placeholder="from(可选)" style="width: 120px" />
            <NInput v-model:value="form.triggerTo" placeholder="to(可选)" style="width: 120px" />
          </template>
          <NSelect v-model:value="form.actionType" :options="actionOptions" style="width: 170px" />
          <NInput
            v-model:value="form.triggerConfigText"
            placeholder='triggerConfig JSON 如 {"to":"in_progress"}'
            style="width: 260px"
          />
          <NInput
            v-model:value="form.actionConfigText"
            placeholder='actionConfig JSON 如 {"priority":"high"}'
            style="width: 260px"
          />
          <NInput
            v-model:value="form.conditionText"
            placeholder='condition JSON 可选 {"priorityIs":"high"}'
            style="width: 240px"
          />
          <NButton type="primary" :loading="creating" @click="createRule">创建规则</NButton>
        </NSpace>

        <NSpace align="center" :wrap="true">
          <span class="text-12px text-gray-500">条件 · 自定义字段</span>
          <NSelect
            v-model:value="form.cfKey"
            clearable
            placeholder="字段 key"
            :options="cfOptions"
            style="width: 200px"
          />
          <NSelect v-model:value="form.cfOp" :options="CF_CONDITION_OPS" style="width: 120px" />
          <NInput
            v-if="cfValueNeeded"
            v-model:value="form.cfValue"
            placeholder="值（JSON 可）"
            style="width: 160px"
          />
          <span class="text-12px text-gray-500">+ AND CF</span>
          <NSelect
            v-model:value="form.extraCfKey"
            clearable
            placeholder="第二字段"
            :options="cfOptions"
            style="width: 180px"
          />
          <NSelect v-model:value="form.extraCfOp" :options="CF_CONDITION_OPS" style="width: 120px" />
          <NInput
            v-if="form.extraCfOp !== 'is_set' && form.extraCfOp !== 'is_empty'"
            v-model:value="form.extraCfValue"
            placeholder="值"
            style="width: 140px"
          />
          <span class="text-12px text-gray-500">动作 · set_custom_field</span>
          <NSelect
            v-model:value="form.actionCfKey"
            clearable
            placeholder="写入字段"
            :options="cfOptions"
            :disabled="form.actionType !== 'set_custom_field'"
            style="width: 200px"
          />
          <NInput
            v-model:value="form.actionCfValue"
            placeholder="写入值"
            :disabled="form.actionType !== 'set_custom_field'"
            style="width: 160px"
          />
        </NSpace>

        <div v-if="!loading && !rows.length" class="text-gray-500 text-14px py-24px text-center">
          暂无自动化规则。创建一条：例如 Issue 创建时自动设自定义字段或优先级。
        </div>
        <NDataTable v-else :columns="columns" :data="rows" :loading="loading" :bordered="false" size="small" />
      </NSpace>
    </NCard>
  </div>
</template>
