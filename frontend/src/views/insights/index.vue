<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import {
  type CycleItem,
  type InsightsSavedReport,
  type InsightsSummary,
  canEditReport,
  countOpenFromStatus,
  createInsightsReport,
  deleteInsightsReport,
  downloadInsightsExport,
  fetchCycles,
  fetchInsightsReports,
  fetchInsightsSummary,
  fetchNotifPrefs,
  fetchProjectList,
  filtersToSummaryParams,
  forkInsightsReport,
  normalizeLabelIds,
  partitionReports,
  patchInsightsReport,
  sumVelocityPoints,
  tagApi,
  updateNotifPrefs,
  type TagItem
} from '@/service/api';
import { useAuthStore } from '@/store/modules/auth';
import { $t } from '@/locales';

defineOptions({ name: 'InsightsPage' });

const authStore = useAuthStore();
const loading = ref(false);
const exporting = ref(false);
const summary = ref<InsightsSummary | null>(null);
const cycles = ref<CycleItem[]>([]);
const projects = ref<Api.Project.Project[]>([]);
const labels = ref<TagItem[]>([]);
const reports = ref<InsightsSavedReport[]>([]);
const selectedCycleId = ref<string | null>(null);
const selectedProjectId = ref<string | null>(null);
const selectedLabelIds = ref<number[]>([]);
const selectedReportId = ref<string | null>(null);
const digestOn = ref(false);
const digestBusy = ref(false);
const saveName = ref('');

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

const currentUserId = computed(() => String(authStore.userInfo.userId || ''));

const partitioned = computed(() => partitionReports(reports.value, currentUserId.value));

const mineReportOptions = computed(() =>
  partitioned.value.mine.map(r => ({
    label: `${r.name}${r.isDefault ? ' ★' : ''}${(r.visibility || 'personal') === 'workspace' ? ' · 已分享' : ''}`,
    value: r.id
  }))
);

const teamReportOptions = computed(() =>
  partitioned.value.shared.map(r => ({
    label: `${r.name} · 团队`,
    value: r.id
  }))
);

const selectedReport = computed(() => reports.value.find(r => r.id === selectedReportId.value) || null);
const selectedCanEdit = computed(() => canEditReport(selectedReport.value, currentUserId.value));
const selectedIsShared = computed(
  () => (selectedReport.value?.visibility || 'personal') === 'workspace'
);

function currentParams() {
  const ids = normalizeLabelIds(selectedLabelIds.value);
  return {
    cycleId: selectedCycleId.value || undefined,
    projectId: selectedProjectId.value || undefined,
    labelIds: ids.length ? ids : undefined
  };
}

function currentFilters() {
  const ids = normalizeLabelIds(selectedLabelIds.value);
  const filters: Record<string, unknown> = {};
  if (selectedProjectId.value) filters.projectId = selectedProjectId.value;
  if (selectedCycleId.value) filters.cycleId = selectedCycleId.value;
  if (ids.length) filters.labelIds = ids;
  return filters;
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

async function loadReports() {
  try {
    const { data, error } = await fetchInsightsReports();
    if (error || !data) {
      reports.value = [];
      return;
    }
    reports.value = data.rows || [];
  } catch {
    reports.value = [];
  }
}

async function loadDigestPref() {
  try {
    const { data, error } = await fetchNotifPrefs();
    if (error || !data) return;
    digestOn.value = Boolean(data.insights_digest);
  } catch {
    digestOn.value = false;
  }
}

async function loadSummary() {
  loading.value = true;
  try {
    const { data, error } = await fetchInsightsSummary(currentParams());
    if (error || !data) {
      window.$message?.error(error?.message || $t('page.shell.insightsLoadFailed'));
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
  selectedReportId.value = null;
  await loadSummary();
}

async function onApplyReport(reportId: string | null) {
  selectedReportId.value = reportId;
  if (!reportId) return;
  const report = reports.value.find(r => r.id === reportId);
  if (!report) return;
  const params = filtersToSummaryParams(report.filters || {});
  selectedProjectId.value = (params.projectId as string) || null;
  selectedCycleId.value = (params.cycleId as string) || null;
  selectedLabelIds.value = normalizeLabelIds(params.labelIds || []);
  await loadSummary();
}

async function onSaveAsReport() {
  const name = (saveName.value || '').trim() || `报表 ${new Date().toLocaleString()}`;
  const { data, error } = await createInsightsReport({
    name,
    filters: currentFilters() as any,
    isDefault: false
  });
  if (error || !data) {
    window.$message?.error(error?.message || '保存失败');
    return;
  }
  saveName.value = '';
  window.$message?.success('已保存到我的报表');
  await loadReports();
  selectedReportId.value = data.id;
}

async function onDeleteReport() {
  if (!selectedReportId.value || !selectedCanEdit.value) return;
  const { error } = await deleteInsightsReport(selectedReportId.value);
  if (error) {
    window.$message?.error(error.message || '删除失败');
    return;
  }
  window.$message?.success('已删除');
  selectedReportId.value = null;
  await loadReports();
}

async function onSetDefaultReport() {
  if (!selectedReportId.value || !selectedCanEdit.value) return;
  const { error } = await patchInsightsReport(selectedReportId.value, { isDefault: true });
  if (error) {
    window.$message?.error(error.message || '设置失败');
    return;
  }
  window.$message?.success('已设为 digest 默认报表');
  await loadReports();
}

async function onToggleShare(shared: boolean) {
  if (!selectedReportId.value || !selectedCanEdit.value) return;
  const { error } = await patchInsightsReport(selectedReportId.value, {
    visibility: shared ? 'workspace' : 'personal'
  });
  if (error) {
    window.$message?.error(error.message || '分享失败');
    return;
  }
  window.$message?.success(shared ? '已分享到团队' : '已取消分享');
  await loadReports();
}

async function onForkReport() {
  if (!selectedReportId.value) return;
  const { data, error } = await forkInsightsReport(selectedReportId.value);
  if (error || !data) {
    window.$message?.error(error?.message || '另存失败');
    return;
  }
  window.$message?.success('已另存为我的报表');
  await loadReports();
  selectedReportId.value = data.id;
}

async function onToggleDigest(v: boolean) {
  digestBusy.value = true;
  try {
    const { data, error } = await updateNotifPrefs({ insights_digest: v });
    if (error || !data) {
      window.$message?.error(error?.message || '保存偏好失败');
      digestOn.value = !v;
      return;
    }
    digestOn.value = Boolean(data.insights_digest);
  } finally {
    digestBusy.value = false;
  }
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
  await Promise.all([loadCycles(), loadProjects(), loadLabels(), loadReports(), loadDigestPref()]);
  await loadSummary();
});
</script>

<template>
  <div class="insights-page">
    <div class="mb-16px flex flex-wrap items-center justify-between gap-12px">
      <div>
        <h2 class="m-0 text-20px font-medium">{{ $t('route.insights') }}</h2>
        <p class="mb-0 mt-4px text-13px opacity-60">
          工作区效能摘要（多标签 OR · 我的/团队报表 · 可选 digest）
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-8px">
        <span class="text-12px ot-muted">{{ $t('route.workflow_projects') }}</span>
        <NSelect
          v-model:value="selectedProjectId"
          clearable
          placeholder="全部项目"
          :options="projectOptions"
          class="filter-select"
          size="small"
          @update:value="onFilterChange"
        />
        <span class="text-12px ot-muted">{{ $t('page.shell.labelsOr') }}</span>
        <NSelect
          v-model:value="selectedLabelIds"
          multiple
          clearable
          filterable
          placeholder="全部标签"
          :options="labelOptions"
          class="filter-select-wide"
          size="small"
          @update:value="onFilterChange"
        />
        <span class="text-12px ot-muted">{{ $t('route.workspace_cycles') }}</span>
        <NSelect
          v-model:value="selectedCycleId"
          clearable
          :placeholder="$t('page.shell.defaultCycle')"
          :options="cycleOptions"
          class="filter-select"
          size="small"
          @update:value="onFilterChange"
        />
        <NButton size="small" secondary :loading="exporting" @click="onExportCsv">导出 CSV</NButton>
      </div>
    </div>

    <div class="mb-16px flex flex-wrap items-center gap-8px rounded-8px bg-[rgba(128,128,128,0.08)] px-12px py-8px">
      <span class="text-12px opacity-70">我的报表</span>
      <NSelect
        :value="selectedReportId"
        clearable
        placeholder="应用已存切片"
        :options="mineReportOptions"
        class="filter-select"
        size="small"
        @update:value="onApplyReport"
      />
      <span class="text-12px opacity-70">团队报表</span>
      <NSelect
        :value="selectedReportId"
        clearable
        placeholder="只读团队切片"
        :options="teamReportOptions"
        class="filter-select"
        size="small"
        @update:value="onApplyReport"
      />
      <NInput v-model:value="saveName" size="small" placeholder="另存为名称" class="filter-select" />
      <NButton size="small" secondary @click="onSaveAsReport">另存为</NButton>
      <NButton
        size="small"
        secondary
        :disabled="!selectedReportId || !selectedCanEdit"
        @click="onSetDefaultReport"
      >
        设为默认
      </NButton>
      <NButton
        size="small"
        tertiary
        :disabled="!selectedReportId || !selectedCanEdit"
        @click="onDeleteReport"
      >
        删除
      </NButton>
      <NButton
        v-if="selectedReportId && selectedCanEdit"
        size="small"
        secondary
        @click="onToggleShare(!selectedIsShared)"
      >
        {{ selectedIsShared ? '取消分享' : '分享到团队' }}
      </NButton>
      <NButton
        v-if="selectedReportId && !selectedCanEdit"
        size="small"
        secondary
        @click="onForkReport"
      >
        另存为我的
      </NButton>
      <span class="mx-4px opacity-30">|</span>
      <span class="text-12px opacity-70">效能 digest</span>
      <NSwitch :value="digestOn" :loading="digestBusy" size="small" @update:value="onToggleDigest" />
      <span class="text-11px opacity-50">默认关；开后由外部 tick 写 Inbox/邮件</span>
    </div>

    <NSpin :show="loading">
      <NEmpty v-if="empty" :description="$t('page.shell.insightsEmpty')" class="py-48px" />

      <template v-else-if="summary">
        <NGrid :x-gap="16" :y-gap="16" cols="1 s:2 m:5" responsive="screen">
          <NGi>
            <NCard size="small">
              <div class="text-12px ot-muted">{{ $t('page.shell.openIssues') }}</div>
              <div class="mt-4px text-26px font-medium">{{ openCount }}</div>
            </NCard>
          </NGi>
          <NGi>
            <NCard size="small">
              <div class="text-12px ot-muted">{{ $t('page.shell.cycleIssues') }}</div>
              <div class="mt-4px text-26px font-medium">
                {{ summary.cycleSnapshot?.issueCount ?? '—' }}
              </div>
              <div class="mt-4px truncate text-12px opacity-50">
                {{ summary.cycleSnapshot?.cycleName || $t('page.shell.noActiveCycle') }}
              </div>
            </NCard>
          </NGi>
          <NGi>
            <NCard size="small">
              <div class="text-12px ot-muted">{{ $t('page.shell.cycleCompleted') }}</div>
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
.filter-select-wide {
  min-width: 220px;
  max-width: 320px;
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
