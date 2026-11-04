<script lang="ts" setup>
import { computed, ref, watch } from 'vue';
import { NButton, NModal, NSpace, NSpin } from 'naive-ui';
import { issuePriorityOptions, issueStatusOptions } from '@/constants/issue';
import { issueApi } from '@/service/api/issue';
import { useIssueFocus } from '@/composables/use-issue-focus';
import { useIssueFieldPickers } from '@/composables/use-issue-field-pickers';
import UserSelect from '@/components/UserSelect.vue';
import type { Api } from '@/typings/api';

defineOptions({ name: 'IssueHotkeyPickerHost' });

const focus = useIssueFocus();
const pickers = useIssueFieldPickers();
const { activePicker, closePicker } = pickers;
const focusedIssueId = focus.focusedIssueId;

const show = computed({
  get: () => activePicker.value !== null,
  set: (v: boolean) => {
    if (!v) closePicker();
  }
});

const title = computed(() => {
  switch (activePicker.value) {
    case 'status':
      return '更改状态';
    case 'assignee':
      return '指派负责人';
    case 'priority':
      return '更改优先级';
    default:
      return '';
  }
});

const submitting = ref(false);
const assigneeId = ref<string | null>(null);

watch(activePicker, kind => {
  if (kind === 'assignee') {
    assigneeId.value = (focus.focusedIssue.value?.assigneeId as string | null | undefined) ?? null;
  }
});

async function applyStatus(status: Api.Issue.IssueStatus) {
  const id = focus.focusedIssueId.value;
  if (!id) return;
  submitting.value = true;
  try {
    const { error } = await issueApi.updateStatus(id, status);
    if (error) {
      window.$message?.error?.(error.message || '更新状态失败');
      return;
    }
    window.$message?.success?.('状态已更新');
    closePicker();
  } finally {
    submitting.value = false;
  }
}

async function applyPriority(priority: Api.Issue.IssuePriority) {
  const id = focus.focusedIssueId.value;
  if (!id) return;
  submitting.value = true;
  try {
    const { error } = await issueApi.updatePriority(id, priority);
    if (error) {
      window.$message?.error?.(error.message || '更新优先级失败');
      return;
    }
    window.$message?.success?.('优先级已更新');
    closePicker();
  } finally {
    submitting.value = false;
  }
}

async function applyAssignee() {
  const id = focus.focusedIssueId.value;
  if (!id) return;
  submitting.value = true;
  try {
    const { error } = await issueApi.updateAssignee(id, assigneeId.value || undefined);
    if (error) {
      window.$message?.error?.(error.message || '指派失败');
      return;
    }
    window.$message?.success?.('负责人已更新');
    closePicker();
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <NModal
    v-model:show="show"
    preset="card"
    :title="title"
    class="issue-hotkey-picker-modal"
    :mask-closable="true"
    @after-leave="closePicker()"
  >
    <NSpin :show="submitting">
      <div v-if="!focusedIssueId" class="picker-empty">无焦点 Issue</div>
      <template v-else-if="activePicker === 'status'">
        <NSpace vertical>
          <NButton
            v-for="opt in issueStatusOptions"
            :key="opt.value"
            block
            secondary
            @click="applyStatus(opt.value as Api.Issue.IssueStatus)"
          >
            {{ opt.label }}
          </NButton>
        </NSpace>
      </template>
      <template v-else-if="activePicker === 'priority'">
        <NSpace vertical>
          <NButton
            v-for="opt in issuePriorityOptions"
            :key="opt.value"
            block
            secondary
            @click="applyPriority(opt.value as Api.Issue.IssuePriority)"
          >
            {{ opt.label }}
          </NButton>
        </NSpace>
      </template>
      <template v-else-if="activePicker === 'assignee'">
        <NSpace vertical>
          <UserSelect v-model="assigneeId" placeholder="选择负责人" clearable />
          <NButton type="primary" block :loading="submitting" @click="applyAssignee">确认指派</NButton>
        </NSpace>
      </template>
    </NSpin>
  </NModal>
</template>

<style scoped>
.issue-hotkey-picker-modal {
  width: 420px;
}

.picker-empty {
  color: var(--color-text-tertiary, #9ca3af);
  font-size: 13px;
}
</style>
