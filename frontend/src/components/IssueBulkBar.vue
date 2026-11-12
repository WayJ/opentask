<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { NButton, NSelect, NSpace, NText } from 'naive-ui';
import { issuePriorityOptions, issueStatusOptions } from '@/constants/issue';
import { issueApi } from '@/service/api/issue';
import { type CycleItem, fetchCycles } from '@/service/api/cycles';
import { type TagItem, tagApi } from '@/service/api/tag';
import { fetchWorkspaceMembers } from '@/service/api/workspace';
import { useIssueSelection } from '@/composables/use-issue-selection';
import { localStg } from '@/utils/storage';
import { $t, i18n } from '@/locales';
import { lookupLabel } from '@/locales/display-label';
import { useLabelTable } from '@/locales/use-label-table';
import type { Api } from '@/typings/api';

defineOptions({ name: 'IssueBulkBar' });

const emit = defineEmits<{ done: [] }>();

const selection = useIssueSelection();
const busy = ref(false);
const status = ref<string | null>(null);
const priority = ref<string | null>(null);
const assigneeId = ref<string | null>(null);
const cycleId = ref<string | null>(null);
const tagIds = ref<number[]>([]);

const cycles = ref<CycleItem[]>([]);
const tags = ref<TagItem[]>([]);
const users = ref<Array<{ label: string; value: string }>>([]);

const locale = i18n.global.locale;
const statusLabels = useLabelTable('page.issueStatus');
const priorityLabels = useLabelTable('page.issuePriority');

const visible = computed(() => selection.hasSelection.value);
const countLabel = computed(() => {
  // eslint-disable-next-line no-void
  void locale.value;
  return $t('page.issueList.bulk.selected', { n: selection.count.value });
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

onMounted(async () => {
  try {
    const wsId = localStg.get('workspaceId') as string | null;
    const [cRes, tRes] = await Promise.all([fetchCycles(), tagApi.list()]);
    cycles.value = cRes.data?.rows || [];
    tags.value = tRes.data?.rows || [];
    if (wsId) {
      const mRes = await fetchWorkspaceMembers(wsId);
      const rows = (mRes.data || []) as Array<{ userId?: string; user_id?: string; name?: string; username?: string }>;
      users.value = rows
        .map(m => ({
          label: m.name || m.username || m.userId || m.user_id || 'user',
          value: String(m.userId || m.user_id || '')
        }))
        .filter(u => u.value);
    }
  } catch {
    /* non-blocking */
  }
});

async function apply() {
  if (!selection.count.value) return;
  const payload: Api.Issue.BulkUpdateIssues = {
    issue_ids: [...selection.selectedIds.value]
  };
  if (status.value) payload.status = status.value as Api.Issue.IssueStatus;
  if (priority.value) payload.priority = priority.value as Api.Issue.IssuePriority;
  if (assigneeId.value) payload.assignee_id = assigneeId.value;
  if (cycleId.value) payload.cycle_id = cycleId.value;
  if (tagIds.value.length) payload.tag_ids = [...tagIds.value];

  if (!payload.status && !payload.priority && !payload.assignee_id && !payload.cycle_id && !payload.tag_ids) {
    window.$message?.warning?.($t('page.issueList.bulk.selectFieldWarning'));
    return;
  }

  busy.value = true;
  try {
    const { error } = await issueApi.bulkUpdateIssues(payload);
    if (error) {
      window.$message?.error?.(error.message || $t('page.issueList.bulk.updateFailed'));
      return;
    }
    window.$message?.success?.($t('page.issueList.bulk.updateSuccess'));
    selection.clear();
    status.value = null;
    priority.value = null;
    assigneeId.value = null;
    cycleId.value = null;
    tagIds.value = [];
    emit('done');
  } catch {
    window.$message?.error?.($t('page.issueList.bulk.updateFailed'));
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div v-if="visible" class="issue-bulk-bar" data-testid="issue-bulk-bar">
    <NText strong>{{ countLabel }}</NText>
    <NSpace align="center" :size="8" wrap>
      <NSelect
        v-model:value="status"
        :options="statusSelectOptions"
        :placeholder="$t('page.issueForm.status')"
        clearable
        size="small"
        style="width: 120px"
      />
      <NSelect
        v-model:value="priority"
        :options="prioritySelectOptions"
        :placeholder="$t('page.issueForm.priority')"
        clearable
        size="small"
        style="width: 110px"
      />
      <NSelect
        v-model:value="assigneeId"
        :options="users"
        :placeholder="$t('page.issueList.columns.assignee')"
        clearable
        filterable
        size="small"
        style="width: 140px"
      />
      <NSelect
        v-model:value="cycleId"
        :options="cycles.map(c => ({ label: c.name, value: c.id }))"
        :placeholder="$t('page.issueForm.cycle')"
        clearable
        size="small"
        style="width: 130px"
      />
      <NSelect
        v-model:value="tagIds"
        :options="tags.map(t => ({ label: t.name, value: t.id }))"
        placeholder="Labels"
        multiple
        clearable
        filterable
        size="small"
        style="min-width: 160px"
      />
      <NButton type="primary" size="small" :loading="busy" @click="apply">
        {{ $t('page.issueList.bulk.apply') }}
      </NButton>
      <NButton size="small" quaternary @click="selection.clear()">{{ $t('common.cancel') }} (Esc)</NButton>
    </NSpace>
  </div>
</template>

<style scoped>
.issue-bulk-bar {
  position: sticky;
  bottom: 12px;
  z-index: 20;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  padding: 10px 14px;
  margin-top: 12px;
  border: 1px solid var(--n-border-color, #e5e7eb);
  border-radius: 10px;
  background: var(--n-color, #fff);
  box-shadow: 0 8px 24px rgb(0 0 0 / 8%);
}
</style>
