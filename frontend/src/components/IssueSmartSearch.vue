<script setup lang="ts">
import { computed } from 'vue';
import { NAutoComplete, NSpace, NText } from 'naive-ui';
import { type ParsedQuery, generateSearchSuggestions, parseSearchString } from '@/utils/issueSearchParser';

interface Props {
  modelValue: string;
  placeholder?: string;
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '搜索问题... (支持 is:open, field:key:value 等)'
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
  search: [query: ParsedQuery, raw: string];
}>();

const searchValue = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value)
});

// 搜索建议
const suggestions = computed(() => {
  if (!searchValue.value) {
    return generateSearchSuggestions();
  }

  const baseSuggestions = generateSearchSuggestions();
  const value = searchValue.value.toLowerCase();

  // 过滤建议
  return baseSuggestions.filter(s => s.toLowerCase().includes(value));
});

// 当前解析的查询
const parsedQuery = computed(() => {
  try {
    return parseSearchString(searchValue.value);
  } catch {
    return {};
  }
});

// 当前应用的过滤器
const activeFilters = computed(() => {
  const filters: string[] = [];
  if (parsedQuery.value.status) filters.push(`状态: ${parsedQuery.value.status}`);
  if (parsedQuery.value.type) filters.push(`类型: ${parsedQuery.value.type}`);
  if (parsedQuery.value.priority) filters.push(`优先级: ${parsedQuery.value.priority}`);
  if (parsedQuery.value.assignee_id) filters.push(`负责人: ${parsedQuery.value.assignee_id}`);
  if (parsedQuery.value.reporter_id) filters.push(`报告人: ${parsedQuery.value.reporter_id}`);
  if (parsedQuery.value.cycle_id) filters.push(`Cycle: ${parsedQuery.value.cycle_id}`);
  if (parsedQuery.value.project_id) filters.push(`项目: ${parsedQuery.value.project_id}`);
  if (parsedQuery.value.labels?.length) filters.push(`标签: ${parsedQuery.value.labels.join(',')}`);
  if (parsedQuery.value.custom_fields?.length) {
    for (const cf of parsedQuery.value.custom_fields) {
      filters.push(`字段 ${cf.key}: ${cf.value}`);
    }
  }
  if (parsedQuery.value.search) filters.push(`搜索: ${parsedQuery.value.search}`);
  return filters;
});

// 执行搜索
function handleSearch() {
  emit('search', parsedQuery.value, searchValue.value || '');
}

// 回车搜索
function handleEnter() {
  handleSearch();
}

// 选择建议
function handleSelect(value: string) {
  searchValue.value = value;
  handleSearch();
}

// 清空搜索
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function handleClear() {
  searchValue.value = '';
  emit('search', {}, '');
}
</script>

<template>
  <div class="issue-smart-search">
    <NSpace vertical :size="12">
      <!-- 搜索框 -->
      <NSpace :size="8">
        <NAutoComplete
          v-model:value="searchValue"
          :options="suggestions"
          :placeholder="props.placeholder"
          :clearable="true"
          size="medium"
          @select="handleSelect"
          @update:value="handleSearch"
          @keydown.enter="handleEnter"
        />
      </NSpace>

      <!-- 当前应用的过滤器 -->
      <div v-if="activeFilters.length > 0" class="active-filters">
        <NSpace :size="4">
          <NText depth="3" style="font-size: 12px">应用过滤器:</NText>
          <NText v-for="(filter, index) in activeFilters" :key="index" type="info" size="small" strong>
            {{ filter }}
          </NText>
        </NSpace>
      </div>
    </NSpace>
  </div>
</template>

<style scoped>
.issue-smart-search {
  width: 100%;
}

.active-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 4px 0;
}
</style>
