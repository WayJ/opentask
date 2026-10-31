<script setup lang="ts">
import { watch } from 'vue';
import { useEcharts } from '@/hooks/common/echarts';

defineOptions({
  name: 'PriorityCharts'
});

interface Props {
  data?: Api.Dashboard.PriorityDistribution[];
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});

const priorityLabels: Record<string, string> = {
  critical: '紧急',
  high: '高',
  medium: '中',
  low: '低',
  none: '未设置'
};

const priorityColors: Record<string, string> = {
  critical: '#ff4d4f',
  high: '#ec4786',
  medium: '#fcbc25',
  low: '#26deca',
  none: '#d9d9d9'
};

const { domRef, updateOptions } = useEcharts(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    top: '10%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: [] as string[]
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      type: 'bar',
      barWidth: '50%',
      data: [] as { value: number; itemStyle: { color: string } }[]
    }
  ]
}));

watch(
  () => props.data,
  newData => {
    if (!newData || newData.length === 0) return;

    updateOptions(opts => {
      opts.xAxis.data = newData.map(item => priorityLabels[item.priority] || item.priority);
      opts.series[0].data = newData.map(item => ({
        value: item.count,
        itemStyle: {
          color: priorityColors[item.priority] || '#8e9dff'
        }
      }));
      return opts;
    });
  },
  { immediate: true }
);
</script>

<template>
  <div class="min-h-300px">
    <div ref="domRef" class="h-300px overflow-hidden"></div>
  </div>
</template>

<style scoped></style>
