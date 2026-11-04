<!-- components/EditableField.vue -->
<script setup lang="ts">
import { computed } from 'vue';
import { NButton, NSelect, NTag } from 'naive-ui';

interface Props {
  modelValue: any;
  editing: boolean;
  label?: string;
  displayValue?: string;
  placeholder?: string;
  options?: Array<{ label: string; value: any }>;
  selectWidth?: string;
  loading?: boolean;
  clearable?: boolean;
  tagType?: 'default' | 'error' | 'info' | 'success' | 'warning';
  readonly?: boolean; // 新增：只读模式
}

interface Emits {
  (e: 'update:modelValue', value: any): void;
  (e: 'update:editing', value: boolean): void;
  (e: 'save'): void;
  (e: 'cancel'): void;
  (e: 'startEdit'): void;
}

const props = withDefaults(defineProps<Props>(), {
  selectWidth: '120px',
  loading: false,
  clearable: false,
  placeholder: '-'
});

const emit = defineEmits<Emits>();

const localValue = computed({
  get: () => props.modelValue,
  set: val => emit('update:modelValue', val)
});

function handleStartEdit() {
  emit('startEdit');
  emit('update:editing', true);
}

function handleSave() {
  emit('save');
  emit('update:editing', false);
}

function handleCancel() {
  emit('cancel');
  emit('update:editing', false);
}
</script>

<template>
  <div class="editable-field">
    <div v-if="label || $slots['label-icon']" class="field-label">
      <slot name="label-icon" />
      <span v-if="label">{{ label }}</span>
    </div>

    <!-- 只读模式 -->
    <div v-if="readonly" class="field-value-readonly">
      <span class="field-value-text">{{ displayValue }}</span>
    </div>

    <!-- 非编辑模式 -->
    <div v-else-if="!editing" class="field-value">
      <NTag v-if="tagType && displayValue" :type="tagType" size="small">
        {{ displayValue }}
      </NTag>
      <span v-else :class="{ 'text-placeholder': !displayValue || displayValue === placeholder }">
        {{ displayValue || placeholder }}
      </span>
      <NButton text size="tiny" @click="handleStartEdit">
        <icon-mdi-pencil />
      </NButton>
    </div>

    <!-- 编辑模式 -->
    <div v-else class="field-edit">
      <slot name="editor">
        <NSelect
          v-if="options"
          v-model:value="localValue"
          :options="options"
          size="small"
          :style="{ width: selectWidth }"
          :loading="loading"
          :clearable="clearable"
        />
      </slot>
      <NButton text size="tiny" type="success" @click="handleSave">
        <icon-mdi-check style="font-size: 18px" />
      </NButton>
      <NButton text size="tiny" @click="handleCancel">
        <icon-mdi-close style="font-size: 18px" />
      </NButton>
    </div>
  </div>
</template>

<style scoped>
.editable-field {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 4px;
  transition: background-color 0.2s ease;
}

.editable-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 4px;
}

.editable-field:hover {
  background-color: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
  padding: 8px 6px;
}

.field-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #666;
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 4.5em;
}

.field-value,
.field-value-readonly {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
}

.field-value-text {
  font-size: 12px;
  color: #333;
  font-weight: 400;
}

.field-edit {
  display: flex;
  align-items: center;
  gap: 4px;
  animation: slideIn 0.15s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-4px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.text-placeholder {
  color: #bbb;
  font-size: 12px;
  font-style: italic;
}

/* 按钮悬停效果 */
.field-value :deep(.n-button) {
  opacity: 0;
  transition: opacity 0.15s ease;
}

.field-value:hover :deep(.n-button) {
  opacity: 1;
}

.field-edit :deep(.n-button) {
  opacity: 1;
}
</style>
