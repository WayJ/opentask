<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import {
  type CycleItem,
  type InsightsSummary,
  countOpenFromStatus,
  downloadInsightsExport,
  fetchCycles,
  fetchInsightsSummary,
  fetchProjectList,
  sumVelocityPoints,
  tagApi,
  type TagItem
} from '@/service/api';

defineOptions({ name: 'InsightsPage' });

const loading = ref(false);
const exporting = ref(false);
const summary = ref<InsightsSummary | null>(null);
const cycles = ref<CycleItem[]>([]);
const projects = ref<Api.Project.Project[]>([]);
const labels = ref<TagItem[]>([]);
const selectedCycleId = ref<string | null>(null);
const selectedProjectId = ref<string | null>(null);
const selectedLabelId = ref<number | null>(null);

const empty = computed(() => {
  if (loading.value || !summary.value) return false;
  const total = Object.values(summary.value.statusCounts || {}).reduce((a, b) => a + Number(b || 0), 0);
  return total === 0;
});

const openCount = computed(() => countOpenFromStatus(summary.value?.statusCounts));

const velocityTotal = computed(() => sumVelocityPoints(summary.value?.estimateVelocity?.buckets));

const statusEntries = computed(() =>
  Object.entries(summary.value?.statusCounts || {})
    .map(([k, v]) => ({ key: k, count: Number(v || 0) }))
    .sort((a, b) => b.count - a.count)
);

const priorityEntries = computed(() =>
  Object.entries(summary.value?.priorityCounts || {})
    .map(([k, v]) => ({ key: k, count: Number(v || 0) }))
    .sort((a, b) => b.count - a.count)
);

const maxStatus = computed(() => Math.max(1, ...statusEntries.value.map(e => e.count)));
const maxPriority = computed(() => Math.max(1, ...priorityEntries.value.map(e => e.count)));
const maxAssignee = computed(() =>
  Math.max(1, ...(summary.value?.assigneeCounts || []).map(a => Number(a.count || 0)))
);
const maxDay = computed(() =>
  Math.max(1, ...(summary.value?.createdVsCompleted || []).flatMap(d => [d.created, d.completed]))
);
const maxVelocity = computed(() =>
  Math.max(1, ...(summary.value?.estimateVelocity?.buckets || []).map(b => Number(b.completedPoints || 0)))
);

const cycleOptions = computed(() =>
  cycles.value.map(c => ({
    label: `${c.name}${c.status === 'active' ? ' · active' : ''}`,
    value: c.id
  }))
);

const projectOptions = computed(() =>
  projects.value.map(p => ({
    label: p.name,
    value: p.id
  }))
);

const labelOptions = computed(() =>
  labels.value.map(t => ({
    label: t.name,
    value: t.id
  }))
);

function currentParams() {
  return {
    cycleId: selectedCycleId.value || undefined,
    projectId: selectedProjectId.value || undefined,
    labelId: selectedLabelId.value ?? undefined
  };
}

async function loadCycles() {
  try {
    const { data, error } = await fetchCycles();
    if (error || !data) return;
    cycles.value = data.rows || [];
    if (!selectedCycleId.value) {
      const active = cycles.value.find(c => c.status === 'active');
      selectedCycleId.value = active?.id || null;
    }
  } catch {
    cycles.value = [];
  }
}

async function loadProjects() {
  try {
    const response = await fetchProjectList();
    projects.value = response.data || [];
  } catch {
    projects.value = [];
  }
}

async function loadLabels() {
  try {
    const { data, error } = await tagApi.list();
    if (error || !data) {
      labels.value = [];
      return;
    }
    labels.value = data.rows || [];
  } catch {
    labels.value = [];
  }
}

async function loadSummary() {
  loading.value = true;
  try {
    const { data, error } = await fetchInsightsSummary(currentParams());
    if (error || !data) {
      window.$message?.error(error?.message || '加载 Insights 失败');
      summary.value = null;
      return;
    }
    summary.value = data;
    if (data.cycleSnapshot?.cycleId && !selectedCycleId.value) {
      selectedCycleId.value = data.cycleSnapshot.cycleId;
    }
  } finally {
    loading.value = false;
  }
}

async function onFilterChange() {
  await loadSummary();
}

async function onExportCsv() {
  exporting.value = true;
  try {
    const blob = await downloadInsightsExport(currentParams());
    const url = URL.createObjectURL(blob as Blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'insights-export.csv';
    a.click();
    URL.revokeObjectURL(url);
    window.$message?.success('已导出 CSV');
  } catch (e) {
    console.error(e);
    window.$message?.error('导出失败');
  } finally {
    exporting.value = false;
  }
}

onMounted(async () => {
  await Promise.all([loadCycles(), loadProjects(), loadLabels()]);
  await loadSummary();
});
</script>

<template>
  <div class="insights-page">
    <div class="mb-16px flex flex-wrap items-center justify-between gap-12px">
      <div>
        <h2 class="m-0 text-20px font-medium">Insights</h2>
        <p class="mb-0 mt-4px text-13px opacity-60">工作区效能摘要（可按项目 / 标签 / Cycle 切片）</p>
      </div>
      <div class="flex flex-wrap items-center gap-8px">
        <span class="text-12px opacity-60">Project</span>
        <NSelect
          v-model:value="selectedProjectId"
          clearable
          placeholder="全部项目"
          :options="projectOptions"
          class="filter-select"
          size="small"
          @update:value="onFilterChange"
        />
        <span class="text-12px opacity-60">Label</span>
        <NSelect
          v-model:value="selectedLabelId"
          clearable
          placeholder="全部标签"
          :options="labelOptions"
          class="filter-select"
          size="small"
          @update:value="onFilterChange"
        />
        <span class="text-12px opacity-60">Cycle</span>
        <NSelect
          v-model:value="selectedCycleId"
          clearable
          placeholder="默认 Active"
          :options="cycleOptions"
          class="filter-select"
          size="small"
          @update:value="onFilterChange"
        />
        <NButton size="small" secondary :loading="exporting" @click="onExportCsv">导出 CSV</NButton>
      </div>
    </div>

    <NSpin :show="loading">
      <NEmpty v-if="empty" description="暂无 Issue。创建几条后回来看分布与趋势。" class="py-48px" />

      <template v-else-if="summary">
        <NGrid :x-gap="16" :y-gap="16" cols="1 s:2 m:5" responsive="screen">
          <NGi>
            <NCard size="small">
              <div class="text-12px opacity-60">开放 Issue</div>
              <div class="mt-4px text-26px font-medium">{{ openCount }}</div>
            </NCard>
          </NGi>
          <NGi>
            <NCard size="small">
              <div class="text-12px opacity-60">Cycle Issues</div>
              <div class="mt-4px text-26px font-medium">
                {{ summary.cycleSnapshot?.issueCount ?? '—' }}
              </div>
              <div class="mt-4px truncate text-12px opacity-50">
                {{ summary.cycleSnapshot?.cycleName || '无 Active Cycle' }}
              </div>
            </NCard>
          </NGi>
          <NGi>
            <NCard size="small">
              <div class="text-12px opacity-60">Cycle 已完成</div>
              <div class="mt-4px text-26px font-medium">
                {{ summary.cycleSnapshot?.completedCount ?? '—' }}
              </div>
            </NCard>
          </NGi>
          <NGi>
            <NCard size="small">
              <div class="text-12px opacity-60">Estimate 点合计</div>
              <div class="mt-4px text-26px font-medium">
                {{ summary.cycleSnapshot ? summary.cycleSnapshot.estimatePointsSum : '—' }}
              </div>
            </NCard>
          </NGi>
          <NGi>
            <NCard size="small">
              <div class="text-12px opacity-60">近 14 日完成估点</div>
              <div class="mt-4px text-26px font-medium">{{ velocityTotal }}</div>
            </NCard>
          </NGi>
        </NGrid>

        <NGrid class="mt-16px" :x-gap="16" :y-gap="16" cols="1 m:2" responsive="screen">
          <NGi>
            <NCard size="small" title="状态分布">
              <div v-if="!statusEntries.length" class="text-12px opacity-50">无数据</div>
              <div v-for="row in statusEntries" :key="row.key" class="mb-10px">
                <div class="mb-4px flex justify-between text-12px">
                  <span>{{ row.key }}</span>
                  <span>{{ row.count }}</span>
                </div>
                <NProgress
                  type="line"
                  :percentage="Math.round((row.count / maxStatus) * 100)"
                  :show-indicator="false"
                  processing
                />
              </div>
            </NCard>
          </NGi>
          <NGi>
            <NCard size="small" title="优先级分布">
              <div v-if="!priorityEntries.length" class="text-12px opacity-50">无数据</div>
              <div v-for="row in priorityEntries" :key="row.key" class="mb-10px">
                <div class="mb-4px flex justify-between text-12px">
                  <span>{{ row.key }}</span>
                  <span>{{ row.count }}</span>
                </div>
                <NProgress
                  type="line"
                  :percentage="Math.round((row.count / maxPriority) * 100)"
                  :show-indicator="false"
                  status="warning"
                />
              </div>
            </NCard>
          </NGi>
        </NGrid>

        <NGrid class="mt-16px" :x-gap="16" :y-gap="16" cols="1 m:2" responsive="screen">
          <NGi>
            <NCard size="small" title="负责人负荷（开放）">
              <div v-if="!(summary.assigneeCounts || []).length" class="text-12px opacity-50">无数据</div>
              <div
                v-for="(row, idx) in summary.assigneeCounts"
                :key="row.assigneeId || `unassigned-${idx}`"
                class="mb-10px"
              >
                <div class="mb-4px flex justify-between text-12px">
                  <span>{{ row.assigneeName }}</span>
                  <span>{{ row.count }}</span>
                </div>
                <NProgress
                  type="line"
                  :percentage="Math.round((row.count / maxAssignee) * 100)"
                  :show-indicator="false"
                  status="success"
                />
              </div>
            </NCard>
          </NGi>
          <NGi>
            <NCard size="small" title="近 14 日 · 创建 vs 完成">
              <div class="trend-table">
                <div class="trend-head">
                  <span>日期</span>
                  <span>创建</span>
                  <span>完成</span>
                  <span>对比</span>
                </div>
                <div v-for="day in summary.createdVsCompleted" :key="day.date" class="trend-row">
                  <span class="mono">{{ day.date.slice(5) }}</span>
                  <span>{{ day.created }}</span>
                  <span>{{ day.completed }}</span>
                  <span class="bars">
                    <i class="bar created" :style="{ width: `${(day.created / maxDay) * 100}%` }" />
                    <i class="bar completed" :style="{ width: `${(day.completed / maxDay) * 100}%` }" />
                  </span>
                </div>
              </div>
            </NCard>
          </NGi>
        </NGrid>

        <NCard class="mt-16px" size="small" title="估点速度 · 近 14 日 completed points">
          <div v-if="!(summary.estimateVelocity?.buckets || []).length" class="text-12px opacity-50">
            无速度数据
          </div>
          <div v-else class="velocity-table">
            <div class="velocity-head">
              <span>日期</span>
              <span>Points</span>
              <span>柱</span>
            </div>
            <div
              v-for="bucket in summary.estimateVelocity?.buckets || []"
              :key="bucket.date"
              class="velocity-row"
            >
              <span class="mono">{{ bucket.date.slice(5) }}</span>
              <span>{{ bucket.completedPoints }}</span>
              <span class="bars">
                <i
                  class="bar velocity"
                  :style="{ width: `${(Number(bucket.completedPoints || 0) / maxVelocity) * 100}%` }"
                />
              </span>
            </div>
          </div>
        </NCard>
      </template>
    </NSpin>
  </div>
</template>

<style scoped>
.insights-page {
  padding: 16px 20px 32px;
}
.filter-select {
  width: 180px;
}
.trend-table,
.velocity-table {
  font-size: 12px;
}
.trend-head,
.trend-row {
  display: grid;
  grid-template-columns: 52px 40px 40px 1fr;
  gap: 8px;
  align-items: center;
  padding: 4px 0;
}
.velocity-head,
.velocity-row {
  display: grid;
  grid-template-columns: 52px 56px 1fr;
  gap: 8px;
  align-items: center;
  padding: 4px 0;
}
.trend-head,
.velocity-head {
  opacity: 0.55;
  border-bottom: 1px solid rgba(128, 128, 128, 0.2);
  margin-bottom: 4px;
}
.mono {
  font-variant-numeric: tabular-nums;
}
.bars {
  position: relative;
  height: 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  justify-content: center;
}
.bar {
  display: block;
  height: 5px;
  border-radius: 2px;
  min-width: 0;
}
.bar.created {
  background: rgba(94, 106, 210, 0.75);
}
.bar.completed {
  background: rgba(24, 160, 88, 0.75);
}
.bar.velocity {
  height: 8px;
  background: rgba(250, 140, 22, 0.8);
}
</style>
