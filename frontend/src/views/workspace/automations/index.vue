<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
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
  fetchAutomations,
  fetchCreateAutomation,
  fetchDeleteAutomation,
  fetchDisableAutomation,
  fetchEnableAutomation,
  parseAutomationJson
} from '@/service/api/automations';

defineOptions({ name: 'WorkspaceAutomationsPage' });

const loading = ref(false);
const rows = ref<AutomationRuleRow[]>([]);
const creating = ref(false);
const form = reactive({
  name: '',
  triggerType: 'issue.created',
  actionType: 'set_priority',
  triggerConfigText: '',
  conditionText: '',
  actionConfigText: '{"priority":"high"}'
});

const triggerOptions = [
  { label: 'issue.created', value: 'issue.created' },
  { label: 'issue.status_changed', value: 'issue.status_changed' },
  { label: 'issue.assignee_changed', value: 'issue.assignee_changed' },
  { label: 'label_added', value: 'label_added' }
];

const actionOptions = [
  { label: 'set_status', value: 'set_status' },
  { label: 'set_assignee', value: 'set_assignee' },
  { label: 'add_label', value: 'add_label' },
  { label: 'set_priority', value: 'set_priority' },
  { label: 'add_comment', value: 'add_comment' }
];

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
    const { data, error } = await fetchAutomations();
    if (error) {
      window.$message?.error?.(error.message || '加载失败');
      return;
    }
    rows.value = data?.rows || [];
  } finally {
    loading.value = false;
  }
}

async function createRule() {
  if (!form.name.trim()) {
    window.$message?.warning?.('请输入名称');
    return;
  }
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
          <NSelect v-model:value="form.actionType" :options="actionOptions" style="width: 160px" />
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
        <div v-if="!loading && !rows.length" class="text-gray-500 text-14px py-24px text-center">
          暂无自动化规则。创建一条：例如 Issue 创建时自动设为 high 优先级。
        </div>
        <NDataTable v-else :columns="columns" :data="rows" :loading="loading" :bordered="false" size="small" />
      </NSpace>
    </NCard>
  </div>
</template>
