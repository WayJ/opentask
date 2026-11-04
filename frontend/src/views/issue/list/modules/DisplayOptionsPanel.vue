<script setup lang="ts">
import { computed } from 'vue';
import { NButton, NCheckbox, NSelect, NSpace, NSwitch, NText } from 'naive-ui';
import {
  DISPLAY_FIELD_KEYS,
  DISPLAY_FIELD_LABELS,
  type ConditionalFormatRule,
  type ConditionalTint,
  type DisplayFieldKey,
  type IssueDisplayFields,
  SWIMLANE_OPTIONS,
  type SwimlaneBy,
  buildSwimlaneOptions
} from '@/utils/display-prefs';

defineOptions({ name: 'DisplayOptionsPanel' });

const props = defineProps<{
  fields: IssueDisplayFields;
  swimlaneBy: SwimlaneBy;
  hideEmptyLanes: boolean;
  saving?: boolean;
  /** E32：可选自定义字段 */
  customFieldOptions?: { key: string; name: string; type?: string }[];
  customFieldKeys?: string[];
  /** E46 */
  conditionalFormats?: ConditionalFormatRule[];
}>();

const emit = defineEmits<{
  'update:fields': [IssueDisplayFields];
  'update:swimlaneBy': [SwimlaneBy];
  'update:hideEmptyLanes': [boolean];
  'update:customFieldKeys': [string[]];
  'update:conditionalFormats': [ConditionalFormatRule[]];
  'set-personal-default': [];
  reset: [];
}>();

const swimlaneOptions = computed(() =>
  buildSwimlaneOptions(
    (props.customFieldOptions || []).map(o => ({
      key: o.key,
      name: o.name,
      type: o.type || 'text'
    }))
  )
);

function toggleField(key: DisplayFieldKey, checked: boolean) {
  emit('update:fields', { ...props.fields, [key]: checked });
}

function toggleCustomField(key: string, checked: boolean) {
  const cur = [...(props.customFieldKeys || [])];
  const idx = cur.indexOf(key);
  if (checked && idx < 0) cur.push(key);
  if (!checked && idx >= 0) cur.splice(idx, 1);
  emit('update:customFieldKeys', cur);
}

function addFormat() {
  const cur = [...(props.conditionalFormats || [])];
  if (cur.length >= 10) return;
  const tint: ConditionalTint = 'warning';
  cur.push({
    id: `cfmt_${Date.now()}`,
    when: { field: 'priority', op: 'eq', value: 'high' },
    style: { rowTint: tint },
    target: 'row'
  });
  emit('update:conditionalFormats', cur);
}

function removeFormat(idx: number) {
  const cur = [...(props.conditionalFormats || [])];
  cur.splice(idx, 1);
  emit('update:conditionalFormats', cur);
}
</script>

<template>
  <div class="display-options-panel">
    <NText strong>显示选项</NText>
    <div class="section">
      <NText depth="3" class="section-title">卡片字段</NText>
      <div class="field-grid">
        <NCheckbox
          v-for="key in DISPLAY_FIELD_KEYS"
          :key="key"
          :checked="fields[key]"
          @update:checked="(v: boolean) => toggleField(key, v)"
        >
          {{ DISPLAY_FIELD_LABELS[key] }}
        </NCheckbox>
      </div>
    </div>
    <div v-if="customFieldOptions?.length" class="section">
      <NText depth="3" class="section-title">自定义字段列</NText>
      <div class="field-grid">
        <NCheckbox
          v-for="opt in customFieldOptions"
          :key="opt.key"
          :checked="(customFieldKeys || []).includes(opt.key)"
          @update:checked="(v: boolean) => toggleCustomField(opt.key, v)"
        >
          {{ opt.name }}
        </NCheckbox>
      </div>
    </div>
    <div class="section">
      <NText depth="3" class="section-title">看板泳道</NText>
      <NSelect
        :value="swimlaneBy"
        :options="swimlaneOptions.length ? swimlaneOptions : SWIMLANE_OPTIONS"
        size="small"
        @update:value="(v: SwimlaneBy) => emit('update:swimlaneBy', v)"
      />
      <div class="hide-empty">
        <NText depth="3">隐藏空泳道</NText>
        <NSwitch
          :value="hideEmptyLanes"
          size="small"
          @update:value="(v: boolean) => emit('update:hideEmptyLanes', v)"
        />
      </div>
    </div>
    <div class="section">
      <NText depth="3" class="section-title">条件格式（≤10）</NText>
      <div v-for="(rule, idx) in conditionalFormats || []" :key="rule.id" class="cfmt-row">
        <NText depth="3" class="cfmt-summary">
          <span class="tint-dot" :data-tint="rule.style.rowTint" />
          {{ rule.when.field }} {{ rule.when.op }} {{ rule.when.value }}
        </NText>
        <NButton size="tiny" quaternary @click="removeFormat(idx)">删</NButton>
      </div>
      <NButton
        size="tiny"
        :disabled="(conditionalFormats || []).length >= 10"
        @click="addFormat"
      >
        添加规则
      </NButton>
    </div>
    <NSpace>
      <NButton size="small" :loading="saving" @click="emit('set-personal-default')">设为个人默认</NButton>
      <NButton size="small" quaternary @click="emit('reset')">重置</NButton>
    </NSpace>
  </div>
</template>

<style scoped>
.display-options-panel {
  width: 280px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 4px;
}
.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.section-title {
  font-size: 12px;
}
.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 8px;
}
.hide-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.cfmt-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.cfmt-summary {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.tint-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  background: #999;
}
.tint-dot[data-tint='danger'] { background: #d03050; }
.tint-dot[data-tint='warning'] { background: #f0a020; }
.tint-dot[data-tint='success'] { background: #18a058; }
.tint-dot[data-tint='info'] { background: #2080f0; }
.tint-dot[data-tint='neutral'] { background: #888; }
</style>
