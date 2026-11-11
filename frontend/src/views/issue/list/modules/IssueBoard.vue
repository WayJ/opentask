<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { NAvatar, NCard, NEmpty, NTag, NText, useMessage } from 'naive-ui';
import { VueDraggable } from 'vue-draggable-plus';
import {
  getIssuePriorityLabel,
  getIssuePriorityTagType,
  getIssueStatusTagType,
  getIssueTypeTagType
} from '@/constants/issue';
import { issueApi } from '@/service/api/issue';
import { useIssueFocus } from '@/composables/use-issue-focus';
import { useIssueSelection } from '@/composables/use-issue-selection';
import { buildIssueDetailLocation } from '@/utils/issue-board-nav';
import { BOARD_STATUS_COLUMNS, type BoardSwimlane, buildBoardSwimlanes } from '@/utils/boardSwimlanes';
import type {
  ColorScaleRule,
  ConditionalFormatRule,
  IconSetRule,
  IssueDisplayFields,
  SwimlaneBy
} from '@/utils/display-prefs';
import { resolveCellIcon, resolveRowBackground } from '@/utils/display-prefs';
import { formatChildProgress } from '@/utils/childProgress';
import type { Api } from '@/typings/api';
import { useLabelTable } from '@/locales/use-label-table';
import { lookupLabel } from '@/locales/display-label';

defineOptions({ name: 'IssueBoard' });

const props = withDefaults(
  defineProps<{
    issues: Api.Issue.Issue[];
    swimlaneBy?: SwimlaneBy;
    hideEmptyLanes?: boolean;
    fields?: IssueDisplayFields;
    conditionalFormats?: ConditionalFormatRule[];
    colorScales?: ColorScaleRule[];
    iconSets?: IconSetRule[];
  }>(),
  {
    swimlaneBy: 'none',
    hideEmptyLanes: false,
    conditionalFormats: () => [],
    colorScales: () => [],
    iconSets: () => [],
    fields: () => ({
      assignee: true,
      priority: true,
      labels: true,
      estimate_points: true,
      due_date: false,
      project: false,
      cycle: false,
      issue_code: true,
      type: false
    })
  }
);

const TINT_BG: Record<string, string> = {
  danger: 'color-mix(in srgb, #d03050 14%, transparent)',
  warning: 'color-mix(in srgb, #f0a020 16%, transparent)',
  success: 'color-mix(in srgb, #18a058 14%, transparent)',
  info: 'color-mix(in srgb, #2080f0 14%, transparent)',
  neutral: 'color-mix(in srgb, #888 12%, transparent)'
};

function cardTintStyle(issue: Api.Issue.Issue): Record<string, string> | undefined {
  const appearance = resolveRowBackground(issue as unknown as Record<string, unknown>, {
    conditionalFormats: props.conditionalFormats,
    colorScales: props.colorScales
  });
  if (!appearance) return undefined;
  if (appearance.kind === 'tint') return { background: TINT_BG[appearance.value] };
  return { background: `color-mix(in srgb, ${appearance.value} 24%, transparent)` };
}

const ICON_GLYPH: Record<string, string> = {
  arrow_up: '↑',
  arrow_down: '↓',
  arrow_flat: '→',
  flag: '⚑',
  dot_red: '●',
  dot_yellow: '●',
  dot_green: '●',
  check: '✓',
  warn: '!'
};

function cardIconPrefix(issue: Api.Issue.Issue): string {
  const icon = resolveCellIcon(issue as unknown as Record<string, unknown>, props.iconSets);
  return icon ? ICON_GLYPH[icon] || '' : '';
}

const issueFocus = useIssueFocus();
const issueSelection = useIssueSelection();

const emit = defineEmits<{
  changed: [];
}>();

const router = useRouter();
const message = useMessage();
const moving = ref(false);

const statusLabels = useLabelTable('page.issueStatus');
const typeLabels = useLabelTable('page.issueType');
const priorityLabels = useLabelTable('page.issuePriority');
const groupLabels = computed(() => ({
  status: statusLabels.value,
  type: typeLabels.value,
  priority: priorityLabels.value
}));
const columns = computed(() =>
  BOARD_STATUS_COLUMNS.map(col => ({
    status: col.status,
    label: lookupLabel(statusLabels.value, col.status)
  }))
);

/** laneKey -> status -> issues (mutable for drag) */
const laneColumnMap = ref<Record<string, Record<string, Api.Issue.Issue[]>>>({});

function rebuild(source: Api.Issue.Issue[]) {
  const lanes = buildBoardSwimlanes(source, props.swimlaneBy, {
    hideEmptyLanes: props.hideEmptyLanes,
    labels: groupLabels.value
  });
  const next: Record<string, Record<string, Api.Issue.Issue[]>> = {};
  for (const lane of lanes) {
    next[lane.key] = {};
    for (const col of BOARD_STATUS_COLUMNS) {
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

watch(
  () => props.issues,
  rows => {
    issueSelection.setIssueOrder((rows || []).map(r => r.id));
  },
  { immediate: true }
);

const lanes = computed<BoardSwimlane[]>(() => {
  return Object.keys(laneColumnMap.value).map(key => {
    const columnsMap = laneColumnMap.value[key] || {};
    const label =
      key === '__all__'
        ? ''
        : buildBoardSwimlanes(props.issues, props.swimlaneBy, { labels: groupLabels.value }).find(l => l.key === key)
            ?.label || key;
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
      <NEmpty description="暂无问题" size="large" />
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
                :style="cardTintStyle(issue)"
                :class="{
                  'is-focused': issueFocus.focusedIssueId === issue.id,
                  'is-selected': issueSelection.isSelected(issue.id)
                }"
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
                <div class="board-card-title">{{ cardIconPrefix(issue) }}{{ issue.title }}</div>
                <div v-if="(issue.blocked_by_count || 0) > 0 || (issue.blocks_count || 0) > 0" class="board-card-meta">
                  <NTag
                    v-if="(issue.blocked_by_count || 0) > 0"
                    size="tiny"
                    type="error"
                    :bordered="false"
                    style="cursor: pointer"
                    @click.stop="openDetail(issue)"
                  >
                    被阻塞 {{ issue.blocked_by_count }}
                  </NTag>
                  <NTag
                    v-if="(issue.blocks_count || 0) > 0"
                    size="tiny"
                    type="warning"
                    :bordered="false"
                    style="cursor: pointer; margin-left: 4px"
                    @click.stop="openDetail(issue)"
                  >
                    阻塞 {{ issue.blocks_count }}
                  </NTag>
                </div>
                <div v-if="formatChildProgress(issue.childProgress)" class="board-card-meta">
                  <NTag size="tiny" type="info" :bordered="false">
                    {{ formatChildProgress(issue.childProgress) }}
                  </NTag>
                </div>
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
                  <NText depth="3" class="text-12px">冲刺 {{ String(issue.cycle_id).slice(0, 8) }}</NText>
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
  border-radius: var(--radius-lg);
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
  border-radius: var(--radius-md);
}

.board-card.is-selected {
  outline: 2px solid color-mix(in srgb, var(--color-primary) 55%, transparent);
  outline-offset: -2px;
  background: color-mix(in srgb, var(--color-primary) 6%, transparent);
}

.board-card.is-focused {
  outline: 2px solid var(--color-primary);
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
