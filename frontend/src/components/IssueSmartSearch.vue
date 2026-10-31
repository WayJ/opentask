<script setup lang="ts">
import { computed } from 'vue';
import { NAutoComplete, NSpace, NText } from 'naive-ui';
import { type ParsedQuery, generateSearchSuggestions, parseSearchString } from '@/utils/issueSearchParser';

interface Props {
  modelValue: string;
  placeholder?: string;
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '搜索 Issue... (支持 is:open, label:bug 等语法)'
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
  search: [query: ParsedQuery];
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
  if (parsedQuery.value.search) filters.push(`搜索: ${parsedQuery.value.search}`);
  return filters;
});

// 执行搜索
function handleSearch() {
  emit('search', parsedQuery.value);
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
  emit('search', {});
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
