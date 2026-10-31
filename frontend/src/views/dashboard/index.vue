<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { fetchDashboardOverview } from '@/service/api/dashboard';
import { useAppStore } from '@/store/modules/app';
import StatCards from './modules/stat-cards.vue';
import StatusCharts from './modules/status-charts.vue';
import TrendChart from './modules/trend-chart.vue';
import PriorityCharts from './modules/priority-charts.vue';
import RecentActivity from './modules/recent-activity.vue';

defineOptions({
  name: 'DevDashboard'
});

const appStore = useAppStore();
const gap = computed(() => (appStore.isMobile ? 0 : 16));

const loading = ref(true);
const dashboardData = ref<Api.Dashboard.DashboardOverview | null>(null);

async function loadDashboard() {
  loading.value = true;
  try {
    const result = await fetchDashboardOverview();
    if (result.data) {
      dashboardData.value = result.data;
    }
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadDashboard();
});
</script>

<template>
  <NSpace vertical :size="16">
    <StatCards :data="dashboardData" :loading="loading" />
    <NGrid :x-gap="gap" :y-gap="16" responsive="screen" item-responsive>
      <NGi span="24 s:24 m:12">
        <NCard :bordered="false" class="card-wrapper" title="需求状态分布">
          <StatusCharts :data="dashboardData?.requirement_by_status" :loading="loading" type="requirement" />
        </NCard>
      </NGi>
      <NGi span="24 s:24 m:12">
        <NCard :bordered="false" class="card-wrapper" title="Issue 类型分布">
          <StatusCharts :data="dashboardData?.issue_by_type" :loading="loading" type="issue" />
        </NCard>
      </NGi>
    </NGrid>
    <NCard :bordered="false" class="card-wrapper" title="近30天创建趋势">
      <TrendChart :data="dashboardData?.trend" :loading="loading" />
    </NCard>
    <NGrid :x-gap="gap" :y-gap="16" responsive="screen" item-responsive>
      <NGi span="24 s:24 m:12">
        <NCard :bordered="false" class="card-wrapper" title="需求优先级分布">
          <PriorityCharts :data="dashboardData?.requirement_by_priority" :loading="loading" />
        </NCard>
      </NGi>
      <NGi span="24 s:24 m:12">
        <NCard :bordered="false" class="card-wrapper" title="Issue 优先级分布">
          <PriorityCharts :data="dashboardData?.issue_by_priority" :loading="loading" />
        </NCard>
      </NGi>
    </NGrid>
    <NCard :bordered="false" class="card-wrapper" title="最近动态">
      <RecentActivity :data="dashboardData?.recent_activities" :loading="loading" />
    </NCard>
  </NSpace>
</template>

<style scoped></style>
