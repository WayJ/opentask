<script setup lang="ts">
import { watch } from 'vue';
import { useEcharts } from '@/hooks/common/echarts';

defineOptions({
  name: 'TrendChart'
});

interface Props {
  data?: Api.Dashboard.TrendDataPoint[];
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});

const { domRef, updateOptions } = useEcharts(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'cross',
      label: {
        backgroundColor: '#6a7985'
      }
    }
  },
  legend: {
    data: ['需求创建', 'Issue 创建'],
    top: '0'
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    top: '15%'
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: [] as string[]
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      color: '#8e9dff',
      name: '需求创建',
      type: 'line',
      smooth: true,
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0.25, color: '#8e9dff' },
            { offset: 1, color: '#fff' }
          ]
        }
      },
      emphasis: { focus: 'series' },
      data: [] as number[]
    },
    {
      color: '#26deca',
      name: 'Issue 创建',
      type: 'line',
      smooth: true,
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0.25, color: '#26deca' },
            { offset: 1, color: '#fff' }
          ]
        }
      },
      emphasis: { focus: 'series' },
      data: [] as number[]
    }
  ]
}));

watch(
  () => props.data,
  newData => {
    if (!newData || newData.length === 0) return;

    updateOptions(opts => {
      opts.xAxis.data = newData.map(item => item.date.substring(5));
      opts.series[0].data = newData.map(item => item.requirement_count);
      opts.series[1].data = newData.map(item => item.issue_count);
      return opts;
    });
  },
  { immediate: true }
);
</script>

<template>
  <div class="min-h-360px">
    <div ref="domRef" class="h-360px overflow-hidden"></div>
  </div>
</template>

<style scoped></style>
