<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NButton, NDatePicker, NInput, NInputNumber, NSelect, NSpace, NSwitch, NText } from 'naive-ui';
import {
  type CustomFieldRow,
  type CustomFieldType,
  type IssueCustomFieldValue,
  fetchPatchIssueCustomFields,
  formatCustomFieldValue
} from '@/service/api/custom-fields';

defineOptions({ name: 'IssueCustomFieldsEditor' });

const props = withDefaults(
  defineProps<{
    issueId?: string | null;
    /** 详情返回的取值（含定义） */
    values?: IssueCustomFieldValue[];
    /** 创建页：仅定义、本地编辑 */
    definitions?: CustomFieldRow[];
    readonly?: boolean;
    /** 创建模式：不立刻 PATCH，向外抛草稿 */
    localOnly?: boolean;
  }>(),
  {
    issueId: null,
    values: () => [],
    definitions: () => [],
    readonly: false,
    localOnly: false
  }
);

const emit = defineEmits<{
  (e: 'updated', rows: IssueCustomFieldValue[]): void;
  (e: 'draft-change', draft: Array<{ key: string; value: unknown }>): void;
}>();

type DraftMap = Record<string, unknown>;

const draft = ref<DraftMap>({});
const saving = ref(false);

const fields = computed(() => {
  if (props.values?.length) {
    return props.values.filter(v => !v.archived || v.value != null);
  }
  return (props.definitions || []).map((d): IssueCustomFieldValue => ({
    fieldId: d.id,
    key: d.key,
    name: d.name,
    type: d.type,
    value: null,
    options: d.options
  }));
});

function syncDraftFromProps() {
  const next: DraftMap = {};
  for (const f of fields.value) {
    next[f.key] = f.value ?? null;
  }
  draft.value = next;
}

watch(fields, syncDraftFromProps, { immediate: true, deep: true });

function optionsFor(f: IssueCustomFieldValue) {
  return (f.options || []).map(o => ({ label: o.label || o.value, value: o.value }));
}

function onLocalChange() {
  if (!props.localOnly) return;
  emit(
    'draft-change',
    Object.entries(draft.value).map(([key, value]) => ({ key, value }))
  );
}

async function saveOne(key: string) {
  if (props.localOnly || !props.issueId || props.readonly) {
    onLocalChange();
    return;
  }
  saving.value = true;
  try {
    const { data, error } = await fetchPatchIssueCustomFields(props.issueId, [
      { key, value: draft.value[key] ?? null }
    ]);
    if (error) {
      window.$message?.error?.(error.message || '保存失败');
      return;
    }
    window.$message?.success?.('已保存');
    if (data?.customFields) emit('updated', data.customFields);
  } finally {
    saving.value = false;
  }
}

function display(type: CustomFieldType, value: unknown) {
  return formatCustomFieldValue(type, value);
}
</script>

<template>
  <div v-if="fields.length" class="issue-custom-fields">
    <div v-for="f in fields" :key="f.fieldId || f.key" class="cf-row">
      <div class="cf-label">
        <NText depth="3" style="font-size: 12px">{{ f.name }}</NText>
        <NText depth="3" style="font-size: 10px; margin-left: 4px">{{ f.key }}</NText>
      </div>
      <div v-if="readonly" class="cf-value">
        <NText>{{ display(f.type, draft[f.key]) }}</NText>
      </div>
      <NSpace v-else align="center" :wrap="false" style="width: 100%">
        <NInput
          v-if="f.type === 'text'"
          v-model:value="draft[f.key] as string"
          size="small"
          placeholder="文本"
          @update:value="onLocalChange"
          @blur="saveOne(f.key)"
        />
        <NInputNumber
          v-else-if="f.type === 'number'"
          v-model:value="draft[f.key] as number | null"
          size="small"
          style="width: 140px"
          @update:value="onLocalChange"
          @blur="saveOne(f.key)"
        />
        <NSwitch
          v-else-if="f.type === 'boolean'"
          :value="Boolean(draft[f.key])"
          size="small"
          @update:value="
            v => {
              draft[f.key] = v;
              onLocalChange();
              saveOne(f.key);
            }
          "
        />
        <NDatePicker
          v-else-if="f.type === 'date'"
          :formatted-value="(draft[f.key] as string) || null"
          value-format="yyyy-MM-dd"
          type="date"
          size="small"
          clearable
          @update:formatted-value="
            v => {
              draft[f.key] = v;
              onLocalChange();
              saveOne(f.key);
            }
          "
        />
        <NSelect
          v-else-if="f.type === 'single_select'"
          v-model:value="draft[f.key] as string | null"
          :options="optionsFor(f)"
          size="small"
          clearable
          style="min-width: 140px"
          @update:value="
            () => {
              onLocalChange();
              saveOne(f.key);
            }
          "
        />
        <NSelect
          v-else-if="f.type === 'multi_select'"
          v-model:value="draft[f.key] as string[] | null"
          :options="optionsFor(f)"
          size="small"
          multiple
          clearable
          style="min-width: 160px"
          @update:value="
            () => {
              onLocalChange();
              saveOne(f.key);
            }
          "
        />
        <NButton v-if="localOnly" text size="tiny" :loading="saving" disabled>草稿</NButton>
      </NSpace>
    </div>
  </div>
  <NText v-else depth="3" style="font-size: 12px">暂无自定义字段。可在「工作区 → 自定义字段」配置。</NText>
</template>

<style scoped>
.issue-custom-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cf-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cf-label {
  display: flex;
  align-items: baseline;
}
</style>
