<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { NCard, NEmpty, NTag, NText, useMessage } from 'naive-ui';
import { VueDraggable } from 'vue-draggable-plus';
import { getIssuePriorityTagType, getIssueStatusTagType, issueStatusOptions } from '@/constants/issue';
import { issueApi } from '@/service/api/issue';
import type { Api } from '@/typings/api';

defineOptions({ name: 'IssueBoard' });

const props = defineProps<{
  issues: Api.Issue.Issue[];
}>();

const emit = defineEmits<{
  changed: [];
}>();

const router = useRouter();
const message = useMessage();
const moving = ref(false);

const columns = issueStatusOptions.map(opt => ({
  status: opt.value as Api.Issue.IssueStatus,
  label: opt.label
}));

/** 各列本地可变列表（拖拽用） */
const columnMap = ref<Record<string, Api.Issue.Issue[]>>({});

function rebuildColumns(source: Api.Issue.Issue[]) {
  const next: Record<string, Api.Issue.Issue[]> = {};
  for (const col of columns) {
    next[col.status] = [];
  }
  const sorted = [...source].sort((a, b) => {
    const pa = a.position ?? Number.MAX_SAFE_INTEGER;
    const pb = b.position ?? Number.MAX_SAFE_INTEGER;
    if (pa !== pb) return pa - pb;
    return String(a.created_at).localeCompare(String(b.created_at));
  });
  for (const issue of sorted) {
    const key = issue.status in next ? issue.status : 'open';
    next[key].push(issue);
  }
  columnMap.value = next;
}

watch(
  () => props.issues,
  list => rebuildColumns(list),
  { immediate: true, deep: true }
);

const totalCards = computed(() => props.issues.length);

function openDetail(issue: Api.Issue.Issue) {
  router.push(`/issue/detail/${issue.id}`);
}

function assigneeLabel(issue: Api.Issue.Issue): string {
  if (issue.assignee?.name) return issue.assignee.name;
  if (issue.assignee?.sso_name) return issue.assignee.sso_name;
  if (issue.assignee_id) return issue.assignee_id.slice(0, 8);
  return '未指派';
}

async function persistColumn(status: Api.Issue.IssueStatus, movedId: string) {
  const list = columnMap.value[status] || [];
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
      rebuildColumns(props.issues);
      return;
    }
    // 乐观校正本地 position/status
    list.forEach((item, idx) => {
      item.status = status;
      item.position = idx;
    });
    emit('changed');
  } catch (e: any) {
    message.error(e?.message || '看板移动失败');
    rebuildColumns(props.issues);
  } finally {
    moving.value = false;
  }
}

async function onColumnChange(status: Api.Issue.IssueStatus, evt: any) {
  // 跨列：added；同列重排：moved
  const addedId = evt?.added?.element?.id as string | undefined;
  const movedId = evt?.moved?.element?.id as string | undefined;
  const targetId = addedId || movedId;
  if (!targetId || moving.value) return;
  await persistColumn(status, targetId);
}
</script>

<template>
  <div class="issue-board" :class="{ 'is-moving': moving }">
    <div v-if="totalCards === 0" class="board-empty">
      <NEmpty description="暂无 Issue" size="large" />
    </div>
    <div v-else class="board-columns">
      <div v-for="col in columns" :key="col.status" class="board-column">
        <div class="board-column-header">
          <NTag size="small" :type="getIssueStatusTagType(col.status)" round>
            {{ col.label }}
          </NTag>
          <NText depth="3" class="board-column-count">
            {{ (columnMap[col.status] || []).length }}
          </NText>
        </div>

        <VueDraggable
          v-model="columnMap[col.status]"
          group="issue-board"
          :animation="150"
          class="board-column-body"
          ghost-class="board-card-ghost"
          :disabled="moving"
          @change="(evt: any) => onColumnChange(col.status, evt)"
        >
          <NCard
            v-for="issue in columnMap[col.status]"
            :key="issue.id"
            size="small"
            hoverable
            class="board-card"
            @click="openDetail(issue)"
          >
            <div class="board-card-code">
              <NText depth="3" class="text-12px">{{ issue.issue_code }}</NText>
              <NTag size="small" :type="getIssuePriorityTagType(issue.priority)" :bordered="false">
                {{ issue.priority }}
              </NTag>
            </div>
            <div class="board-card-title">{{ issue.title }}</div>
            <div class="board-card-meta">
              <icon-mdi-account-outline class="meta-icon" />
              <NText depth="3" class="text-12px">{{ assigneeLabel(issue) }}</NText>
            </div>
          </NCard>
        </VueDraggable>
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

.board-columns {
  display: flex;
  gap: 12px;
  min-height: 420px;
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
}

.meta-icon {
  font-size: 14px;
  color: var(--color-text-tertiary, #9ca3af);
}

.board-card-ghost {
  opacity: 0.5;
}
</style>
