<script setup lang="ts">
import { computed } from 'vue';
import { useThemeStore } from '@/store/modules/theme';

defineOptions({
  name: 'StatCards'
});

interface Props {
  data?: Api.Dashboard.DashboardOverview | null;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});

interface StatItem {
  key: string;
  title: string;
  value: number;
  subLabel: string;
  subValue: number;
  color: { start: string; end: string };
  icon: string;
}

const themeStore = useThemeStore();

// eslint-disable-next-line complexity
const cardData = computed<StatItem[]>(() => [
  {
    key: 'req_total',
    title: '需求总数',
    value: props.data?.requirements?.total ?? 0,
    subLabel: '待处理',
    subValue: props.data?.requirements?.open_count ?? 0,
    color: { start: '#56cdf3', end: '#719de3' },
    icon: 'ant-design:file-text-outlined'
  },
  {
    key: 'issue_total',
    title: 'Issue 总数',
    value: props.data?.issues?.total ?? 0,
    subLabel: '待处理',
    subValue: props.data?.issues?.open_count ?? 0,
    color: { start: '#ec4786', end: '#b955a4' },
    icon: 'ant-design:bug-outlined'
  },
  {
    key: 'req_completed',
    title: '需求已完成',
    value: props.data?.requirements?.completed_count ?? 0,
    subLabel: '进行中',
    subValue: props.data?.requirements?.in_progress_count ?? 0,
    color: { start: '#26deca', end: '#36d3b3' },
    icon: 'ant-design:check-circle-outlined'
  },
  {
    key: 'issue_completed',
    title: 'Issue 已解决',
    value: props.data?.issues?.completed_count ?? 0,
    subLabel: '进行中',
    subValue: props.data?.issues?.in_progress_count ?? 0,
    color: { start: '#fcbc25', end: '#f68057' },
    icon: 'ant-design:thunderbolt-outlined'
  }
]);

function getGradientColor(color: StatItem['color']) {
  return `linear-gradient(to bottom right, ${color.start}, ${color.end})`;
}
</script>

<template>
  <NCard :bordered="false" size="small" class="card-wrapper">
    <NSpin :show="loading">
      <NGrid cols="s:1 m:2 l:4" responsive="screen" :x-gap="16" :y-gap="16">
        <NGi v-for="item in cardData" :key="item.key">
          <div
            class="px-16px pb-4px pt-8px text-white"
            :style="{
              backgroundImage: getGradientColor(item.color),
              borderRadius: themeStore.themeRadius + 'px'
            }"
          >
            <h3 class="text-16px">{{ item.title }}</h3>
            <div class="flex justify-between pt-12px">
              <SvgIcon :icon="item.icon" class="text-32px" />
              <CountTo :start-value="0" :end-value="item.value" class="text-30px text-white dark:text-dark" />
            </div>
            <p class="mt-4px text-12px opacity-80">{{ item.subLabel }}: {{ item.subValue }}</p>
          </div>
        </NGi>
      </NGrid>
    </NSpin>
  </NCard>
</template>

<style scoped></style>
