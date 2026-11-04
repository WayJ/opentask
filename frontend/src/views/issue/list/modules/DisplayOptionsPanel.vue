<script setup lang="ts">
import { NButton, NCheckbox, NSelect, NSpace, NSwitch, NText } from 'naive-ui';
import {
  DISPLAY_FIELD_KEYS,
  DISPLAY_FIELD_LABELS,
  type DisplayFieldKey,
  type IssueDisplayFields,
  SWIMLANE_OPTIONS,
  type SwimlaneBy
} from '@/utils/display-prefs';

defineOptions({ name: 'DisplayOptionsPanel' });

const props = defineProps<{
  fields: IssueDisplayFields;
  swimlaneBy: SwimlaneBy;
  hideEmptyLanes: boolean;
  saving?: boolean;
}>();

const emit = defineEmits<{
  'update:fields': [IssueDisplayFields];
  'update:swimlaneBy': [SwimlaneBy];
  'update:hideEmptyLanes': [boolean];
  'set-personal-default': [];
  reset: [];
}>();

function toggleField(key: DisplayFieldKey, checked: boolean) {
  emit('update:fields', { ...props.fields, [key]: checked });
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
    <div class="section">
      <NText depth="3" class="section-title">看板泳道</NText>
      <NSelect
        :value="swimlaneBy"
        :options="SWIMLANE_OPTIONS"
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
</style>
