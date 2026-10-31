<script setup lang="ts">
import { watch } from 'vue';
import { useEcharts } from '@/hooks/common/echarts';

defineOptions({
  name: 'StatusCharts'
});

interface Props {
  data?: Api.Dashboard.StatusDistribution[] | Api.Dashboard.TypeDistribution[];
  loading?: boolean;
  type: 'requirement' | 'issue';
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});

const statusColors: Record<string, string> = {
  planning: '#8e9dff',
  generating: '#26deca',
  evaluating: '#fcbc25',
  completed: '#36d3b3',
  closed: '#56cdf3',
  archived: '#b955a4',
  open: '#ec4786',
  in_progress: '#f68057',
  feedback: '#865ec0',
  resolved: '#26deca',
  rejected: '#ff4d4f',
  bug: '#ec4786',
  feature: '#56cdf3',
  question: '#fcbc25',
  feedback_type: '#865ec0',
  incident: '#ff4d4f',
  improvement: '#26deca'
};

const statusLabels: Record<string, string> = {
  planning: '规划中',
  generating: '生成中',
  evaluating: '评估中',
  completed: '已完成',
  closed: '已关闭',
  archived: '已归档',
  open: '待处理',
  in_progress: '进行中',
  feedback: '反馈中',
  resolved: '已解决',
  rejected: '已拒绝',
  bug: 'Bug',
  feature: '功能',
  question: '问题',
  feedback_type: '反馈',
  incident: '事故',
  improvement: '改进'
};

const { domRef, updateOptions } = useEcharts(() => ({
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c} ({d}%)'
  },
  legend: {
    bottom: '1%',
    left: 'center',
    itemStyle: {
      borderWidth: 0
    }
  },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 6,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: false,
        position: 'center'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: '14',
          fontWeight: 'bold'
        }
      },
      labelLine: {
        show: false
      },
      data: [] as { name: string; value: number; itemStyle: { color: string } }[]
    }
  ]
}));

watch(
  () => props.data,
  newData => {
    if (!newData || newData.length === 0) return;

    updateOptions(opts => {
      const key = props.type === 'requirement' ? 'status' : 'type';
      opts.series[0].data = newData.map(item => ({
        name: statusLabels[(item as any)[key]] || (item as any)[key],
        value: item.count,
        itemStyle: {
          color: statusColors[(item as any)[key]] || '#8e9dff'
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
