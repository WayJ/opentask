<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NCollapse, NCollapseItem, NDataTable, NEmpty, NTag, NText } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { type GroupByKey, type IssueGroupBucket, groupIssuesBy } from '@/utils/groupIssuesBy';
import { nestIssuesDepth1 } from '@/utils/nestIssuesDepth1';
import { $t } from '@/locales';
import { useLabelTable } from '@/locales/use-label-table';
import type { Api } from '@/typings/api';

defineOptions({ name: 'IssueListGrouped' });

const props = defineProps<{
  issues: Api.Issue.Issue[];
  groupBy: Exclude<GroupByKey, 'none'>;
  columns: DataTableColumns<Api.Issue.Issue>;
  rowProps?: (row: Api.Issue.Issue) => Record<string, unknown>;
}>();

const typeLabels = useLabelTable('page.issueType');
const statusLabels = useLabelTable('page.issueStatus');
const priorityLabels = useLabelTable('page.issuePriority');
const buckets = computed<IssueGroupBucket[]>(() =>
  groupIssuesBy(props.issues, props.groupBy, {
    type: typeLabels.value,
    status: statusLabels.value,
    priority: priorityLabels.value
  })
);

function nestBucketIssues(list: Api.Issue.Issue[]) {
  return nestIssuesDepth1(list).map(r => ({ ...r.issue, nestDepth: r.depth }));
}

/** 默认全部展开 */
const expandedNames = ref<string[]>([]);

watch(
  buckets,
  next => {
    expandedNames.value = next.map(b => b.key);
  },
  { immediate: true }
);
</script>

<template>
  <div class="issue-list-grouped">
    <NEmpty v-if="buckets.length === 0" :description="$t('page.shell.noIssues')" size="large" />
    <NCollapse v-else v-model:expanded-names="expandedNames" display-directive="show">
      <NCollapseItem v-for="bucket in buckets" :key="bucket.key" :name="bucket.key">
        <template #header>
          <div class="lane-header">
            <NText strong>{{ bucket.label }}</NText>
            <NTag size="small" round :bordered="false" type="info">
              {{ bucket.issues.length }}
            </NTag>
          </div>
        </template>
        <NDataTable
          :columns="columns"
          :data="nestBucketIssues(bucket.issues)"
          :row-key="(row: Api.Issue.Issue) => row.id"
          :row-props="props.rowProps"
          :scroll-x="1400"
          striped
          size="small"
        />
      </NCollapseItem>
    </NCollapse>
    <NText depth="3" class="lane-hint">
      {{ $t('page.issueList.board.groupedListHint') }}
    </NText>
  </div>
</template>

<style scoped>
.issue-list-grouped {
  width: 100%;
}

.lane-header {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.lane-hint {
  display: block;
  margin-top: 12px;
  font-size: 12px;
  color: var(--color-text-tertiary, #9ca3af);
}

:deep(.n-collapse-item) {
  margin-bottom: 8px;
  background: var(--color-bg-primary, #fff);
  border: 1px solid var(--color-border-subtle, #e5e7eb);
  border-radius: 12px;
  overflow: hidden;
}

:deep(.n-collapse-item__header) {
  padding: 12px 16px !important;
  background: var(--color-bg-secondary, #f7f8fa);
}

:deep(.n-collapse-item__content-inner) {
  padding: 8px 12px 12px !important;
}
</style>
