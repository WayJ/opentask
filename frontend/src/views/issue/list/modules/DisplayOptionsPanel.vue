<script setup lang="ts">
import { computed } from 'vue';
import { NButton, NCheckbox, NSelect, NSpace, NSwitch, NText } from 'naive-ui';
import {
  DISPLAY_FIELD_KEYS,
  type ColorScaleRule,
  type ConditionalFormatRule,
  type ConditionalTint,
  type DisplayFieldKey,
  type IconSetRule,
  type IssueDisplayFields,
  SWIMLANE_OPTIONS,
  type SwimlaneBy,
  buildSwimlaneOptions
} from '@/utils/display-prefs';
import { $t, i18n } from '@/locales';

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
  /** E49 */
  colorScales?: ColorScaleRule[];
  iconSets?: IconSetRule[];
}>();

const emit = defineEmits<{
  'update:fields': [IssueDisplayFields];
  'update:swimlaneBy': [SwimlaneBy];
  'update:hideEmptyLanes': [boolean];
  'update:customFieldKeys': [string[]];
  'update:conditionalFormats': [ConditionalFormatRule[]];
  'update:colorScales': [ColorScaleRule[]];
  'update:iconSets': [IconSetRule[]];
  'set-personal-default': [];
  reset: [];
}>();

const locale = i18n.global.locale;

function displayFieldLabel(key: DisplayFieldKey): string {
  switch (key) {
    case 'issue_code':
      return $t('page.issueList.columns.key');
    case 'assignee':
      return $t('page.issueList.columns.assignee');
    case 'priority':
      return $t('page.issueList.columns.priority');
    case 'labels':
      return $t('page.issueList.groupBy.label');
    case 'type':
      return $t('page.issueList.columns.type');
    case 'estimate_points':
      return $t('page.issueList.columns.estimate');
    case 'due_date':
      return $t('page.issueForm.dueDate');
    case 'project':
      return $t('page.issueList.filters.project');
    case 'cycle':
      return $t('page.issueList.displayOptions.fieldCycle');
    default: {
      const unreachable: never = key;
      return unreachable;
    }
  }
}

function swimlaneOptionLabel(option: { label: string; value: string }): string {
  if (option.value === 'none') return $t('page.issueList.displayOptions.noSwimlane');
  if (option.value === 'assignee') return $t('page.issueList.groupBy.assignee');
  if (option.value === 'priority') return $t('page.issueList.groupBy.priority');
  if (option.value === 'type') return $t('page.issueList.groupBy.type');
  if (option.value === 'label') return $t('page.issueList.groupBy.label');
  if (option.label.endsWith('（计算值·只读）')) {
    const suffix = '（计算值·只读）';
    return `${option.label.slice(0, -suffix.length)}${$t('page.issueList.computedFieldSuffixReadonly')}`;
  }
  return option.label;
}

const swimlaneOptions = computed(() =>
  buildSwimlaneOptions(
    (props.customFieldOptions || []).map(o => ({
      key: o.key,
      name: o.name,
      type: o.type || 'text'
    }))
  )
);

const fieldLabelByKey = computed(() => {
  // eslint-disable-next-line no-void
  void locale.value;
  const labels = {} as Record<DisplayFieldKey, string>;
  for (const key of DISPLAY_FIELD_KEYS) labels[key] = displayFieldLabel(key);
  return labels;
});

const localizedSwimlaneOptions = computed(() => {
  // eslint-disable-next-line no-void
  void locale.value;
  const source = swimlaneOptions.value.length ? swimlaneOptions.value : SWIMLANE_OPTIONS;
  return source.map(option => ({ ...option, label: swimlaneOptionLabel(option) }));
});

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

function addColorScale() {
  const cur = [...(props.colorScales || [])];
  if (cur.length >= 5) return;
  cur.push({
    id: `cscale_${Date.now()}`,
    field: 'estimate_points',
    domain: { min: 0, max: 10 },
    palette: 'blue_red',
    target: 'row'
  });
  emit('update:colorScales', cur);
}

function removeColorScale(idx: number) {
  const cur = [...(props.colorScales || [])];
  cur.splice(idx, 1);
  emit('update:colorScales', cur);
}

function addIconSet() {
  const cur = [...(props.iconSets || [])];
  if (cur.length >= 5) return;
  cur.push({
    id: `iset_${Date.now()}`,
    field: 'priority',
    rules: [{ op: 'eq', value: 'high', icon: 'flag' }]
  });
  emit('update:iconSets', cur);
}

function removeIconSet(idx: number) {
  const cur = [...(props.iconSets || [])];
  cur.splice(idx, 1);
  emit('update:iconSets', cur);
}
</script>

<template>
  <div class="display-options-panel">
    <NText strong>{{ $t('page.issueList.displayOptions.title') }}</NText>
    <div class="section">
      <NText depth="3" class="section-title">{{ $t('page.issueList.displayOptions.cardFields') }}</NText>
      <div class="field-grid">
        <NCheckbox
          v-for="key in DISPLAY_FIELD_KEYS"
          :key="key"
          :checked="fields[key]"
          @update:checked="(v: boolean) => toggleField(key, v)"
        >
          {{ fieldLabelByKey[key] }}
        </NCheckbox>
      </div>
    </div>
    <div v-if="customFieldOptions?.length" class="section">
      <NText depth="3" class="section-title">{{ $t('page.issueList.displayOptions.customFieldColumns') }}</NText>
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
      <NText depth="3" class="section-title">{{ $t('page.issueList.displayOptions.boardSwimlanes') }}</NText>
      <NSelect
        :value="swimlaneBy"
        :options="localizedSwimlaneOptions"
        size="small"
        @update:value="(v: SwimlaneBy) => emit('update:swimlaneBy', v)"
      />
      <div class="hide-empty">
        <NText depth="3">{{ $t('page.issueList.displayOptions.hideEmptyLanes') }}</NText>
        <NSwitch
          :value="hideEmptyLanes"
          size="small"
          @update:value="(v: boolean) => emit('update:hideEmptyLanes', v)"
        />
      </div>
    </div>
    <div class="section">
      <NText depth="3" class="section-title">{{ $t('page.issueList.displayOptions.conditionalFormats') }}</NText>
      <div v-for="(rule, idx) in conditionalFormats || []" :key="rule.id" class="cfmt-row">
        <NText depth="3" class="cfmt-summary">
          <span class="tint-dot" :data-tint="rule.style.rowTint" />
          {{ rule.when.field }} {{ rule.when.op }} {{ rule.when.value }}
        </NText>
        <NButton size="tiny" quaternary @click="removeFormat(idx)">
          {{ $t('page.issueList.displayOptions.remove') }}
        </NButton>
      </div>
      <NButton size="tiny" :disabled="(conditionalFormats || []).length >= 10" @click="addFormat">
        {{ $t('page.issueList.displayOptions.addRule') }}
      </NButton>
    </div>
    <div class="section">
      <NText depth="3" class="section-title">{{ $t('page.issueList.displayOptions.colorScales') }}</NText>
      <div v-for="(scale, idx) in colorScales || []" :key="scale.id" class="cfmt-row">
        <NText depth="3" class="cfmt-summary">
          {{ scale.field }} · {{ scale.palette }} · [{{ scale.domain.min }},{{ scale.domain.max }}]
        </NText>
        <NButton size="tiny" quaternary @click="removeColorScale(idx)">
          {{ $t('page.issueList.displayOptions.remove') }}
        </NButton>
      </div>
      <NButton size="tiny" :disabled="(colorScales || []).length >= 5" @click="addColorScale">
        {{ $t('page.issueList.displayOptions.addColorScale') }}
      </NButton>
    </div>
    <div class="section">
      <NText depth="3" class="section-title">{{ $t('page.issueList.displayOptions.iconSets') }}</NText>
      <div v-for="(iset, idx) in iconSets || []" :key="iset.id" class="cfmt-row">
        <NText depth="3" class="cfmt-summary">
          {{ iset.field }} · {{ $t('page.issueList.displayOptions.ruleCount', { n: iset.rules.length }) }}
        </NText>
        <NButton size="tiny" quaternary @click="removeIconSet(idx)">
          {{ $t('page.issueList.displayOptions.remove') }}
        </NButton>
      </div>
      <NButton size="tiny" :disabled="(iconSets || []).length >= 5" @click="addIconSet">
        {{ $t('page.issueList.displayOptions.addIconSet') }}
      </NButton>
    </div>
    <NSpace>
      <NButton size="small" :loading="saving" @click="emit('set-personal-default')">
        {{ $t('page.issueList.displayOptions.setPersonalDefault') }}
      </NButton>
      <NButton size="small" quaternary @click="emit('reset')">{{ $t('common.reset') }}</NButton>
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
