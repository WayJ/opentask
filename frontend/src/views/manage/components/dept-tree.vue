<script setup lang="tsx">
import { computed, ref, watch } from 'vue';
import { fetchGetDeptTree } from '@/service/api';

/**
 * 部门树（manage/user 与 manage/dept 共用）
 *
 * - showAll：在树顶追加「全部」虚拟节点（用户页按部门筛选成员用），select 事件回传 null
 * - 选中态由父组件通过 v-model:selectedId 控制（NTree 选中行 = accent-soft 浅底）
 * - 停用部门在名称后附 muted 小字标记
 */

interface Props {
  /** 树顶是否追加「全部」虚拟节点 */
  showAll?: boolean;
  /** 选中部门 id；null 表示选中「全部」 */
  selectedId?: string | null;
  /** 「全部」节点的显示文案 */
  allLabel?: string;
}

const props = withDefaults(defineProps<Props>(), {
  showAll: false,
  selectedId: null,
  allLabel: '全部'
});

interface Emits {
  (e: 'update:selectedId', id: string | null): void;
  (e: 'select', id: string | null): void;
}

const emit = defineEmits<Emits>();

const ALL_KEY = '__all__';

// 部门树原始数据（蛇形命名，与后端一致）
const depts = ref<Api.SystemManage.Department[]>([]);
const treeLoading = ref(false);
const expandedKeys = ref<string[]>([]);

/** 后端树节点 → NTree 数据（label 为名称；停用部门带后缀标记） */
function toTreeOption(node: Api.SystemManage.Department) {
  return {
    key: node.id,
    label: node.name,
    status: node.status,
    children: (node.children || []).map(toTreeOption)
  };
}

/** 全量展平树节点（初始化展开用） */
function flattenKeys(nodes: Api.SystemManage.Department[], acc: string[] = []): string[] {
  nodes.forEach(node => {
    acc.push(node.id);
    if (node.children?.length) flattenKeys(node.children, acc);
  });
  return acc;
}

const treeData = computed(() => {
  const options = depts.value.map(toTreeOption);
  if (!props.showAll) return options;
  return [{ key: ALL_KEY, label: props.allLabel, status: 1, children: options }];
});

const selectedKeys = computed(() => {
  if (props.showAll && !props.selectedId) return [ALL_KEY];
  return props.selectedId ? [props.selectedId] : [];
});

/** 拉取部门树并默认全部展开 */
async function reload() {
  treeLoading.value = true;
  const { error, data } = await fetchGetDeptTree();
  if (!error && data) {
    depts.value = data;
    expandedKeys.value = flattenKeys(data);
  }
  treeLoading.value = false;
}

function handleSelect(keys: string[], option: { key: string | number } | null) {
  const key = String(option?.key ?? keys[0] ?? ALL_KEY);
  const id = key === ALL_KEY ? null : key;
  emit('update:selectedId', id);
  emit('select', id);
}

// NTree render-label：停用部门追加 muted「停用」小字
function renderLabel({ option }: { option: { label: string; status?: number } }) {
  if (option.status === 0) {
    return (
      <span class="dept-tree__label">
        {option.label}
        <span class="dept-tree__disabled">停用</span>
      </span>
    );
  }
  return <span class="dept-tree__label">{option.label}</span>;
}

watch(
  () => props.showAll,
  () => reload(),
  { immediate: true }
);

defineExpose({ reload });
</script>

<template>
  <div class="dept-tree">
    <NTree
      :data="treeData"
      :selected-keys="selectedKeys"
      :expanded-keys="expandedKeys"
      :loading="treeLoading"
      block-line
      :expand-on-click="true"
      :render-label="renderLabel"
      @update:selected-keys="handleSelect"
      @update:expanded-keys="(keys: Array<string | number>) => (expandedKeys = keys.map(String))"
    />
  </div>
</template>

<style scoped>
/* 部门树：选中行 accent-soft 浅底、圆角 7px（DESIGN 控件圆角） */
.dept-tree :deep(.n-tree-node) {
  border-radius: var(--vk-radius-control);
}

.dept-tree :deep(.n-tree-node--selected .n-tree-node-content) {
  background: var(--vk-accent-soft);
}

.dept-tree :deep(.n-tree-node--selected .n-tree-node-content .n-tree-node__label) {
  color: var(--vk-accent-ink);
}

.dept-tree__label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--vk-font-dense);
}

.dept-tree__disabled {
  font-size: var(--vk-font-micro);
  color: var(--vk-muted);
  background: var(--vk-soft);
  border-radius: var(--vk-radius-micro);
  padding: 0 4px;
  line-height: 16px;
}
</style>
