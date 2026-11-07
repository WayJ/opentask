<script lang="ts" setup>
import { computed, ref, watch } from 'vue';
import { NButton, NCheckbox, NModal, NSpace, NSpin, NTag } from 'naive-ui';
import { issuePriorityOptions, issueStatusOptions } from '@/constants/issue';
import { issueApi } from '@/service/api/issue';
import { type TagItem, tagApi } from '@/service/api/tag';
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
    case 'labels':
      return '设置标签';
    case 'estimate':
      return '设置估点';
    default:
      return '';
  }
});

const submitting = ref(false);
const assigneeId = ref<string | null>(null);
const availableTags = ref<TagItem[]>([]);
const selectedTagIds = ref<number[]>([]);
const tagsLoading = ref(false);

watch(activePicker, async kind => {
  if (kind === 'assignee') {
    assigneeId.value = (focus.focusedIssue.value?.assigneeId as string | null | undefined) ?? null;
  }
  if (kind === 'labels') {
    tagsLoading.value = true;
    selectedTagIds.value = [];
    try {
      const listRes = await tagApi.list();
      availableTags.value = listRes.data?.rows || [];
      const id = focus.focusedIssueId.value;
      if (id) {
        const cur = await issueApi.getTags(id);
        const rows = cur.data?.rows || [];
        selectedTagIds.value = rows
          .map((t: Api.Issue.IssueTag) => Number(t.id ?? t.tag_id))
          .filter(n => !Number.isNaN(n));
      }
    } catch {
      availableTags.value = [];
    } finally {
      tagsLoading.value = false;
    }
  }
});

function toggleTag(id: number, checked: boolean) {
  if (checked) {
    if (!selectedTagIds.value.includes(id)) selectedTagIds.value = [...selectedTagIds.value, id];
  } else {
    selectedTagIds.value = selectedTagIds.value.filter(x => x !== id);
  }
}

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

const estimateOptions = [1, 2, 3, 5, 8, 13, 21];

async function applyEstimate(points: number | null) {
  const id = focus.focusedIssueId.value;
  if (!id) return;
  submitting.value = true;
  try {
    const { error } = await issueApi.updateIssue(id, { estimate_points: points });
    if (error) {
      window.$message?.error?.(error.message || '更新估点失败');
      return;
    }
    window.$message?.success?.('估点已更新');
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

async function applyLabels() {
  const id = focus.focusedIssueId.value;
  if (!id) return;
  submitting.value = true;
  try {
    const { error } = await issueApi.replaceTags(id, selectedTagIds.value);
    if (error) {
      window.$message?.error?.(error.message || '更新标签失败');
      return;
    }
    window.$message?.success?.('标签已更新');
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
    <NSpin :show="submitting || tagsLoading">
      <div v-if="!focusedIssueId" class="picker-empty">无焦点问题</div>
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
      <template v-else-if="activePicker === 'labels'">
        <NSpace vertical>
          <div v-if="!availableTags.length" class="picker-empty">暂无标签，请先到 Labels 设置页创建</div>
          <div v-for="tag in availableTags" :key="tag.id" class="label-row">
            <NCheckbox
              :checked="selectedTagIds.includes(tag.id)"
              @update:checked="(v: boolean) => toggleTag(tag.id, v)"
            >
              <NTag size="small" :bordered="false" :style="{ background: tag.color, color: '#fff' }">
                {{ tag.name }}
              </NTag>
            </NCheckbox>
          </div>
          <NButton type="primary" block :loading="submitting" @click="applyLabels">确认</NButton>
        </NSpace>
      </template>
      <template v-else-if="activePicker === 'estimate'">
        <NSpace vertical>
          <NButton v-for="pts in estimateOptions" :key="pts" block secondary @click="applyEstimate(pts)">
            {{ pts }} 点
          </NButton>
          <NButton block quaternary @click="applyEstimate(null)">清除估点</NButton>
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

.label-row {
  display: flex;
  align-items: center;
}
</style>
