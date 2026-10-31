<!-- frontend/src/views/issue/detail/components/DescriptionCard.vue -->
<script setup lang="ts">
import { ref } from 'vue';
import { NButton, NCard, NEmpty, NInput } from 'naive-ui';

interface Issue {
  id: string;
  description: string;
}

interface Props {
  issue: Issue;
  editable?: boolean;
}

interface Emits {
  (e: 'update', value: string): void;
}

const props = withDefaults(defineProps<Props>(), {
  editable: true
});

const emit = defineEmits<Emits>();

const isEditing = ref(false);
const editingValue = ref('');

const startEdit = () => {
  editingValue.value = props.issue.description || '';
  isEditing.value = true;
};

const saveEdit = () => {
  emit('update', editingValue.value);
  isEditing.value = false;
};

const cancelEdit = () => {
  editingValue.value = '';
  isEditing.value = false;
};
</script>

<template>
  <NCard class="description-card" title="📝 描述">
    <template #header-extra>
      <NButton v-if="editable" quaternary size="small" @click="startEdit">
        <template #icon>
          <icon-mdi-pencil />
        </template>
        编辑
      </NButton>
    </template>

    <div v-if="!isEditing" class="description-view">
      <div v-if="!issue.description" class="empty-state">
        <NEmpty description="暂无描述">
          <template #extra>
            <NButton size="small" @click="startEdit">添加描述</NButton>
          </template>
        </NEmpty>
      </div>
      <div v-else class="description-content">
        <pre class="description-text">{{ issue.description }}</pre>
      </div>
    </div>

    <div v-else class="description-edit">
      <NInput v-model:value="editingValue" type="textarea" :rows="8" placeholder="输入问题描述..." />
      <div class="edit-actions">
        <NButton type="primary" size="small" @click="saveEdit">保存</NButton>
        <NButton size="small" @click="cancelEdit">取消</NButton>
      </div>
    </div>
  </NCard>
</template>

<style scoped>
.description-card {
  box-shadow: var(--shadow-sm);
}

.description-edit {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.edit-actions {
  display: flex;
  gap: var(--space-sm);
}

.description-view {
  min-height: 100px;
}

.empty-state {
  padding: var(--space-2xl) 0;
}

.description-content {
  padding: var(--space-md) 0;
}

.description-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  line-height: 1.6;
  color: var(--color-text-primary);
  margin: 0;
}
</style>
