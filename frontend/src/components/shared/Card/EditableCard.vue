<!-- frontend/src/components/shared/Card/EditableCard.vue -->
<script setup lang="ts">
import { ref } from 'vue';
import { NButton } from 'naive-ui';

interface Props {
  modelValue: string;
  editable?: boolean;
}

interface Emits {
  (e: 'update:modelValue', value: string): void;
  (e: 'save', value: string): void;
  (e: 'cancel'): void;
}

const props = withDefaults(defineProps<Props>(), {
  editable: true
});

const emit = defineEmits<Emits>();

const isEditing = ref(false);
const internalValue = ref(props.modelValue);

const startEdit = () => {
  internalValue.value = props.modelValue;
  isEditing.value = true;
};

const updateValue = (value: string) => {
  internalValue.value = value;
};

const saveEdit = () => {
  emit('update:modelValue', internalValue.value);
  emit('save', internalValue.value);
  isEditing.value = false;
};

const cancelEdit = () => {
  internalValue.value = props.modelValue;
  emit('cancel');
  isEditing.value = false;
};

defineExpose({
  startEdit,
  cancelEdit
});
</script>

<template>
  <div class="editable-card">
    <div v-if="!isEditing" class="editable-card__view">
      <slot name="view" />
      <NButton v-if="editable" quaternary size="small" class="editable-card__edit-btn" @click="startEdit">
        <template #icon>
          <icon-mdi-pencil />
        </template>
        编辑
      </NButton>
    </div>

    <div v-else class="editable-card__edit">
      <slot name="edit" :value="internalValue" :update="updateValue" :cancel="cancelEdit" :save="saveEdit" />
    </div>
  </div>
</template>

<style scoped>
.editable-card {
  position: relative;
}

.editable-card__view {
  position: relative;
}

.editable-card__edit-btn {
  position: absolute;
  top: var(--space-sm);
  right: var(--space-sm);
  opacity: 0;
  transition: opacity 0.2s;
}

.editable-card__view:hover .editable-card__edit-btn {
  opacity: 1;
}

.editable-card__edit {
  animation: expand 0.2s ease-out;
}

@keyframes expand {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
