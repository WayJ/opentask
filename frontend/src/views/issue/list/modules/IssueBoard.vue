<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { NCard, NEmpty, NTag, NText, useMessage } from 'naive-ui';
import { VueDraggable } from 'vue-draggable-plus';
import { getIssuePriorityLabel, getIssuePriorityTagType, getIssueStatusTagType, getIssueTypeTagType } from '@/constants/issue';
import { issueApi } from '@/service/api/issue';
import { useIssueFocus } from '@/composables/use-issue-focus';
import { buildIssueDetailLocation } from '@/utils/issue-board-nav';
import { BOARD_STATUS_COLUMNS, type BoardSwimlane, buildBoardSwimlanes } from '@/utils/boardSwimlanes';
import type { IssueDisplayFields, SwimlaneBy } from '@/utils/display-prefs';
import type { Api } from '@/typings/api';

defineOptions({ name: 'IssueBoard' });

const props = withDefaults(
  defineProps<{
    issues: Api.Issue.Issue[];
    swimlaneBy?: SwimlaneBy;
    hideEmptyLanes?: boolean;
    fields?: IssueDisplayFields;
  }>(),
  {
    swimlaneBy: 'none',
    hideEmptyLanes: false,
    fields: () => ({
      assignee: true,
      priority: true,
      labels: true,
      estimate_points: false,
      due_date: false,
      project: false,
      cycle: false,
      issue_code: true,
      type: false
    })
  }
);

const issueFocus = useIssueFocus();

const emit = defineEmits<{
  changed: [];
}>();

const router = useRouter();
const message = useMessage();
const moving = ref(false);

const columns = BOARD_STATUS_COLUMNS;

/** laneKey -> status -> issues (mutable for drag) */
const laneColumnMap = ref<Record<string, Record<string, Api.Issue.Issue[]>>>({});

function rebuild(source: Api.Issue.Issue[]) {
  const lanes = buildBoardSwimlanes(source, props.swimlaneBy, props.hideEmptyLanes);
  const next: Record<string, Record<string, Api.Issue.Issue[]>> = {};
  for (const lane of lanes) {
    next[lane.key] = {};
    for (const col of columns) {
      next[lane.key][col.status] = [...(lane.columns[col.status] || [])];
    }
  }
  laneColumnMap.value = next;
}

watch(
  () => [props.issues, props.swimlaneBy, props.hideEmptyLanes] as const,
  () => rebuild(props.issues),
  { immediate: true, deep: true }
);

const lanes = computed<BoardSwimlane[]>(() => {
  return Object.keys(laneColumnMap.value).map(key => {
    const columnsMap = laneColumnMap.value[key] || {};
    const label =
      key === '__all__'
        ? ''
        : buildBoardSwimlanes(props.issues, props.swimlaneBy, false).find(l => l.key === key)?.label || key;
    return { key, label, columns: columnsMap };
  });
});

const totalCards = computed(() => props.issues.length);
const showLaneHeaders = computed(() => props.swimlaneBy !== 'none');

function focusIssue(issue: Api.Issue.Issue) {
  issueFocus.setFocus(issue.id, {
    title: issue.title,
    status: issue.status,
    priority: issue.priority,
    assigneeId: issue.assignee_id
  });
}

function openDetail(issue: Api.Issue.Issue) {
  focusIssue(issue);
  router.push(buildIssueDetailLocation(issue.id));
}

function assigneeLabel(issue: Api.Issue.Issue): string {
  if (issue.assignee?.name) return issue.assignee.name;
  if (issue.assignee?.sso_name) return issue.assignee.sso_name;
  if (issue.assignee_id) return issue.assignee_id.slice(0, 8);
  return '未指派';
}

function tagNames(issue: Api.Issue.Issue): string {
  const tags = (issue as Api.Issue.Issue & { tags?: Array<{ name?: string }> }).tags;
  if (!Array.isArray(tags) || !tags.length) return '';
  return tags
    .map(t => t.name)
    .filter(Boolean)
    .join(', ');
}

async function persistColumn(laneKey: string, status: Api.Issue.IssueStatus, movedId: string) {
  const list = laneColumnMap.value[laneKey]?.[status] || [];
  const position = list.findIndex(i => i.id === movedId);
  if (position < 0) return;

  moving.value = true;
  try {
    const { error } = await issueApi.moveOnBoard({
      issue_id: movedId,
      status,
      position,
      ordered_ids: list.map(i => i.id)
    });
    if (error) {
      message.error(error.message || '看板移动失败');
      rebuild(props.issues);
      return;
    }
    list.forEach((item, idx) => {
      item.status = status;
      item.position = idx;
    });
    emit('changed');
  } catch (e: any) {
    message.error(e?.message || '看板移动失败');
    rebuild(props.issues);
  } finally {
    moving.value = false;
  }
}

async function onColumnChange(laneKey: string, status: Api.Issue.IssueStatus, evt: any) {
  const addedId = evt?.added?.element?.id as string | undefined;
  const movedId = evt?.moved?.element?.id as string | undefined;
  const targetId = addedId || movedId;
  if (!targetId || moving.value) return;
  await persistColumn(laneKey, status, targetId);
}

function showField(key: keyof IssueDisplayFields): boolean {
  return props.fields?.[key] !== false;
}
</script>

<template>
  <div class="issue-board" :class="{ 'is-moving': moving }">
    <div v-if="totalCards === 0" class="board-empty">
      <NEmpty description="暂无 Issue" size="large" />
    </div>
    <div v-else class="board-lanes">
      <div v-for="lane in lanes" :key="lane.key" class="board-lane">
        <div v-if="showLaneHeaders" class="board-lane-header">
          <NText strong>{{ lane.label || lane.key }}</NText>
          <NText depth="3" class="board-lane-count">
            {{ columns.reduce((n, c) => n + (lane.columns[c.status] || []).length, 0) }}
          </NText>
        </div>
        <div class="board-columns">
          <div v-for="col in columns" :key="`${lane.key}-${col.status}`" class="board-column">
            <div class="board-column-header">
              <NTag size="small" :type="getIssueStatusTagType(col.status)" round>
                {{ col.label }}
              </NTag>
              <NText depth="3" class="board-column-count">
                {{ (lane.columns[col.status] || []).length }}
              </NText>
            </div>

            <VueDraggable
              v-model="laneColumnMap[lane.key][col.status]"
              :group="`issue-board-${lane.key}`"
              :animation="150"
              class="board-column-body"
              ghost-class="board-card-ghost"
              :disabled="moving"
              @change="(evt: any) => onColumnChange(lane.key, col.status, evt)"
            >
              <NCard
                v-for="issue in lane.columns[col.status]"
                :key="issue.id"
                size="small"
                hoverable
                class="board-card"
                :class="{ 'is-focused': issueFocus.focusedIssueId === issue.id }"
                @click="focusIssue(issue)"
                @dblclick="openDetail(issue)"
              >
                <div v-if="showField('issue_code') || showField('priority')" class="board-card-code">
                  <NText v-if="showField('issue_code')" depth="3" class="text-12px">{{ issue.issue_code }}</NText>
                  <NTag
                    v-if="showField('priority')"
                    size="small"
                    :type="getIssuePriorityTagType(issue.priority)"
                    :bordered="false"
                  >
                    {{ getIssuePriorityLabel(issue.priority) }}
                  </NTag>
                </div>
                <div class="board-card-title">{{ issue.title }}</div>
                <div v-if="showField('type')" class="board-card-meta">
                  <NTag size="small" :type="getIssueTypeTagType(issue.type)" :bordered="false">
                    {{ issue.type }}
                  </NTag>
                </div>
                <div v-if="showField('assignee')" class="board-card-meta">
                  <icon-mdi-account-outline class="meta-icon" />
                  <NText depth="3" class="text-12px">{{ assigneeLabel(issue) }}</NText>
                </div>
                <div v-if="showField('labels') && tagNames(issue)" class="board-card-meta">
                  <icon-mdi-tag-outline class="meta-icon" />
                  <NText depth="3" class="text-12px">{{ tagNames(issue) }}</NText>
                </div>
                <div v-if="showField('estimate_points') && issue.estimate_points != null" class="board-card-meta">
                  <NText depth="3" class="text-12px">估点 {{ issue.estimate_points }}</NText>
                </div>
                <div v-if="showField('due_date') && issue.due_date" class="board-card-meta">
                  <NText depth="3" class="text-12px">截止 {{ issue.due_date }}</NText>
                </div>
                <div v-if="showField('project') && issue.project_id" class="board-card-meta">
                  <NText depth="3" class="text-12px">项目 {{ String(issue.project_id).slice(0, 8) }}</NText>
                </div>
                <div v-if="showField('cycle') && issue.cycle_id" class="board-card-meta">
                  <NText depth="3" class="text-12px">Cycle {{ String(issue.cycle_id).slice(0, 8) }}</NText>
                </div>
              </NCard>
            </VueDraggable>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.issue-board {
  width: 100%;
  overflow-x: auto;
}

.issue-board.is-moving {
  opacity: 0.85;
  pointer-events: none;
}

.board-empty {
  padding: 48px 0;
}

.board-lanes {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.board-lane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 4px 8px;
}

.board-lane-count {
  font-size: 12px;
}

.board-columns {
  display: flex;
  gap: 12px;
  min-height: 200px;
  padding-bottom: 8px;
}

.board-column {
  flex: 0 0 260px;
  width: 260px;
  background: var(--color-bg-secondary, #f7f8fa);
  border: 1px solid var(--color-border-subtle, #e5e7eb);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 280px);
}

.board-column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--color-border-subtle, #e5e7eb);
}

.board-column-count {
  font-size: 12px;
}

.board-column-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.board-card {
  cursor: grab;
  border-radius: 8px;
}

.board-card.is-focused {
  outline: 2px solid var(--primary-color, #18a058);
  outline-offset: 1px;
}

.board-card:active {
  cursor: grabbing;
}

.board-card-code {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.board-card-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary, #111827);
  line-height: 1.4;
  margin-bottom: 8px;
  word-break: break-word;
}

.board-card-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}

.meta-icon {
  font-size: 14px;
  color: var(--color-text-tertiary, #9ca3af);
}

.board-card-ghost {
  opacity: 0.5;
}
</style>
