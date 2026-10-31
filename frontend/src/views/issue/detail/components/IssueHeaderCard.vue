<!-- frontend/src/views/issue/detail/components/IssueHeaderCard.vue -->
<script setup lang="ts">
import { NButton, NCard } from 'naive-ui';

interface Issue {
  id: string;
  issue_code: string;
  title: string;
  status: string;
}

interface Props {
  issue: Issue;
}

interface Emits {
  (e: 'refresh'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const goBack = () => {
  window.history.back();
};

const handleEdit = () => {
  window.location.href = `/issue/edit?id=${props.issue.id}`;
};

const handleStatusChange = () => {
  emit('refresh');
};
</script>

<template>
  <NCard class="issue-header-card" :bordered="true">
    <div class="header-top">
      <div class="header-left">
        <NButton quaternary circle @click="goBack">
          <template #icon>
            <icon-mdi-arrow-left />
          </template>
        </NButton>
        <div class="title-info">
          <div class="issue-code">
            <span class="code-dot"></span>
            {{ issue.issue_code }}
          </div>
          <h1 class="issue-title">{{ issue.title }}</h1>
        </div>
      </div>
      <div class="header-actions">
        <NButton size="medium" @click="handleEdit">
          <template #icon>
            <icon-mdi-pencil />
          </template>
          编辑
        </NButton>
        <NButton size="medium" @click="handleStatusChange">
          <template #icon>
            <icon-mdi-swap-horizontal />
          </template>
          改状态
        </NButton>
      </div>
    </div>
  </NCard>
</template>

<style scoped>
.issue-header-card {
  box-shadow: var(--shadow-sm);
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-lg);
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
  flex: 1;
  min-width: 0;
}

.title-info {
  flex: 1;
  min-width: 0;
}

.issue-code {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xs);
}

.code-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
}

.issue-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.4;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .header-top {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
