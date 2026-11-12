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
import { $t, locale } from '@/locales';
import { lookupLabel } from '@/locales/display-label';
import { useLabelTable } from '@/locales/use-label-table';

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

const statusLabels = useLabelTable('page.issueStatus');
const priorityLabels = useLabelTable('page.issuePriority');

const title = computed(() => {
  // eslint-disable-next-line no-void
  void locale.value;
  switch (activePicker.value) {
    case 'status':
      return $t('page.shell.hotkeyPicker.changeStatus');
    case 'assignee':
      return $t('page.shell.hotkeyPicker.assignOwner');
    case 'priority':
      return $t('page.shell.hotkeyPicker.changePriority');
    case 'labels':
      return $t('page.shell.hotkeyPicker.setLabels');
    case 'estimate':
      return $t('page.shell.hotkeyPicker.setEstimate');
    default:
      return '';
  }
});

const statusSelectOptions = computed(() => {
  // eslint-disable-next-line no-void
  void locale.value;
  return issueStatusOptions.map(option => ({
    ...option,
    label: lookupLabel(statusLabels.value, option.value)
  }));
});

const prioritySelectOptions = computed(() => {
  // eslint-disable-next-line no-void
  void locale.value;
  return issuePriorityOptions.map(option => ({
    ...option,
    label: lookupLabel(priorityLabels.value, option.value)
  }));
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
      window.$message?.error?.(error.message || $t('page.shell.hotkeyPicker.updateStatusFailed'));
      return;
    }
    window.$message?.success?.($t('page.shell.hotkeyPicker.statusUpdated'));
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
      window.$message?.error?.(error.message || $t('page.shell.hotkeyPicker.updateEstimateFailed'));
      return;
    }
    window.$message?.success?.($t('page.shell.hotkeyPicker.estimateUpdated'));
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
      window.$message?.error?.(error.message || $t('page.shell.hotkeyPicker.updatePriorityFailed'));
      return;
    }
    window.$message?.success?.($t('page.shell.hotkeyPicker.priorityUpdated'));
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
      window.$message?.error?.(error.message || $t('page.shell.hotkeyPicker.assignFailed'));
      return;
    }
    window.$message?.success?.($t('page.shell.hotkeyPicker.ownerUpdated'));
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
      window.$message?.error?.(error.message || $t('page.shell.hotkeyPicker.updateLabelsFailed'));
      return;
    }
    window.$message?.success?.($t('page.shell.hotkeyPicker.labelsUpdated'));
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
      <div v-if="!focusedIssueId" class="picker-empty">{{ $t('page.shell.hotkeyPicker.noFocusedIssue') }}</div>
      <template v-else-if="activePicker === 'status'">
        <NSpace vertical>
          <NButton
            v-for="opt in statusSelectOptions"
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
            v-for="opt in prioritySelectOptions"
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
          <UserSelect v-model="assigneeId" :placeholder="$t('page.shell.hotkeyPicker.selectOwner')" clearable />
          <NButton type="primary" block :loading="submitting" @click="applyAssignee">
            {{ $t('page.shell.hotkeyPicker.confirmAssign') }}
          </NButton>
        </NSpace>
      </template>
      <template v-else-if="activePicker === 'labels'">
        <NSpace vertical>
          <div v-if="!availableTags.length" class="picker-empty">
            {{ $t('page.shell.hotkeyPicker.noLabels') }}
          </div>
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
          <NButton type="primary" block :loading="submitting" @click="applyLabels">{{ $t('common.confirm') }}</NButton>
        </NSpace>
      </template>
      <template v-else-if="activePicker === 'estimate'">
        <NSpace vertical>
          <NButton v-for="pts in estimateOptions" :key="pts" block secondary @click="applyEstimate(pts)">
            {{ $t('page.shell.hotkeyPicker.points', { n: pts }) }}
          </NButton>
          <NButton block quaternary @click="applyEstimate(null)">
            {{ $t('page.shell.hotkeyPicker.clearEstimate') }}
          </NButton>
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
