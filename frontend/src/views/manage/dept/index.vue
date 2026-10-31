<script setup lang="tsx">
import { computed, reactive, ref, watch } from 'vue';
import { NButton, NSpace } from 'naive-ui';
import {
  fetchDeleteDept,
  fetchGetDeptTree,
  fetchGetUsers,
  fetchUpdateDept,
  fetchUpdateDeptStatus
} from '@/service/api';
import { useAuth } from '@/hooks/business/auth';
import DeptTree from '../components/dept-tree.vue';
import DeptEditDrawer from './modules/dept-edit-drawer.vue';

/**
 * 部门管理（Phase 5 Task 3，DESIGN：左部门树 260px + 右详情卡）
 *
 * - 右侧详情：部门信息（name/sort/status 编辑保存）+ 成员列表（按部门拉用户）
 *   + 子部门管理（列表 + 新建子部门）
 * - 删除需确认；后端 409（有成员/子部门）时展示后端原因
 */

const { hasAuth } = useAuth();

// 部门树原始数据（蛇形命名）
const deptTree = ref<Api.SystemManage.Department[]>([]);
const selectedDeptId = ref<string | null>(null);
const treeRef = ref<InstanceType<typeof DeptTree> | null>(null);

/** 全量展平树节点 → id 映射 */
function flattenDepts(
  nodes: Api.SystemManage.Department[],
  acc: Record<string, Api.SystemManage.Department> = {},
  parentName = ''
) {
  nodes.forEach(node => {
    acc[node.id] = { ...node, name: parentName ? `${parentName} / ${node.name}` : node.name };
    if (node.children?.length) flattenDepts(node.children, acc, node.name);
  });
  return acc;
}

const deptMap = computed(() => flattenDepts(deptTree.value));
const selectedDept = computed(() => (selectedDeptId.value ? deptMap.value[selectedDeptId.value] : null));
// 直接子部门（用原始树数据，避免拼接名）
const childDepts = computed(() => {
  if (!selectedDeptId.value) return [];
  const find = (nodes: Api.SystemManage.Department[]): Api.SystemManage.Department[] => {
    for (const node of nodes) {
      if (node.id === selectedDeptId.value) return node.children || [];
      const hit = find(node.children || []);
      if (hit) return hit;
    }
    return [];
  };
  return find(deptTree.value);
});

async function loadTree(selectId?: string) {
  const { error, data } = await fetchGetDeptTree();
  if (!error && data) {
    deptTree.value = data;
    // 保持选中；选中节点被删时回退到第一个根部门
    if (selectId) {
      selectedDeptId.value = selectId;
    } else if (selectedDeptId.value && !deptMap.value[selectedDeptId.value]) {
      selectedDeptId.value = data[0]?.id || null;
    } else if (!selectedDeptId.value && data.length) {
      selectedDeptId.value = data[0].id;
    }
  }
  // 左侧树组件内部维护同一棵树的数据副本，同步刷新
  treeRef.value?.reload();
}

function handleSelect(id: string | null) {
  selectedDeptId.value = id;
}

// ===== 部门信息编辑 =====
const deptForm = reactive({
  name: '',
  sort: 0,
  status: 1 as 0 | 1
});
const saving = ref(false);

watch(
  selectedDept,
  dept => {
    deptForm.name = dept?.name?.split(' / ').pop() || '';
    deptForm.sort = dept?.sort ?? 0;
    deptForm.status = (dept?.status ?? 1) as 0 | 1;
  },
  { immediate: true }
);

async function handleSaveDept() {
  if (!selectedDeptId.value) return;
  if (!deptForm.name.trim()) {
    window.$message?.warning('部门名称不能为空');
    return;
  }
  saving.value = true;
  const { error } = await fetchUpdateDept(selectedDeptId.value, {
    name: deptForm.name.trim(),
    sort: deptForm.sort
  });
  // 状态变化走独立接口（后端启禁用复用 manage:dept:update 权限码）
  if (!error && deptForm.status !== selectedDept.value?.status) {
    const statusResp = await fetchUpdateDeptStatus(selectedDeptId.value, deptForm.status);
    if (statusResp.error) {
      window.$message?.error('状态更新失败');
    }
  }
  saving.value = false;
  if (!error) {
    window.$message?.success('部门信息已保存');
    loadTree(selectedDeptId.value);
  }
}

// ===== 成员列表 =====
const members = ref<Api.SystemManage.User[]>([]);
const memberLoading = ref(false);

async function loadMembers() {
  if (!selectedDeptId.value) {
    members.value = [];
    return;
  }
  memberLoading.value = true;
  const { error, data } = await fetchGetUsers({
    current: 1,
    pageSize: 50,
    dept_id: selectedDeptId.value
  });
  if (!error && data) {
    members.value = data.rows;
  }
  memberLoading.value = false;
}

watch(selectedDeptId, () => loadMembers());

// 角色编码列表：优先 roleCodes，存量用户回退 role 字符串
function getRoleCodes(row: Api.SystemManage.User): string[] {
  if (row.roleCodes?.length) return row.roleCodes;
  if (row.role) return [row.role];
  return [];
}

function memberRowKey(row: Api.SystemManage.User) {
  return row.id;
}

const memberColumns = [
  {
    key: 'username',
    title: '账号',
    width: 130,
    render: (row: Api.SystemManage.User) => row.username || row.jnpfAccount || '-'
  },
  {
    key: 'name',
    title: '姓名',
    width: 120,
    render: (row: Api.SystemManage.User) => row.name || row.jnpfName || '-'
  },
  {
    key: 'roles',
    title: '角色',
    minWidth: 120,
    render: (row: Api.SystemManage.User) => {
      const codes = getRoleCodes(row);
      return codes.length ? (
        <NSpace size={4}>
          {codes.map((code: string) => (
            <span key={code} class="vk-role-tag">
              {code}
            </span>
          ))}
        </NSpace>
      ) : (
        <span class="vk-muted-text">未分配</span>
      );
    }
  },
  {
    key: 'status',
    title: '状态',
    width: 80,
    render: (row: Api.SystemManage.User) => (
      <span class={`vk-status ${row.status === 1 ? 'vk-status--success' : 'vk-status--muted'}`}>
        <i class="vk-status__dot" />
        {row.status === 1 ? '启用' : '禁用'}
      </span>
    )
  }
];

// ===== 新建 / 删除 =====
const drawerVisible = ref(false);
const createParentId = ref<string | null>(null);
const createParentName = ref('');

function handleCreateRoot() {
  createParentId.value = null;
  createParentName.value = '';
  drawerVisible.value = true;
}

function handleCreateChild() {
  createParentId.value = selectedDeptId.value;
  createParentName.value = selectedDept.value?.name?.split(' / ').pop() || '';
  drawerVisible.value = true;
}

function handleDrawerSubmitted(newId?: string) {
  loadTree(newId || selectedDeptId.value || undefined);
}

// 从 flat request 的 AxiosError 中取后端 detail（409 冲突原因等）
function getErrMsg(err: unknown, fallback: string) {
  const e = err as { response?: { data?: { detail?: string } }; message?: string } | null;
  return e?.response?.data?.detail || e?.message || fallback;
}

function handleDeleteDept(dept: Api.SystemManage.Department) {
  window.$dialog?.warning({
    title: '删除部门',
    content: `确认删除部门「${dept.name}」吗？删除后不可恢复。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const { error } = await fetchDeleteDept(dept.id);
      if (!error) {
        window.$message?.success('部门已删除');
        if (selectedDeptId.value === dept.id) {
          selectedDeptId.value = null;
        }
        loadTree();
      } else {
        // 后端 409：存在子部门 / 仍有成员时给出具体原因
        window.$message?.error(getErrMsg(error, '删除失败'));
      }
    }
  });
}

function handleDeleteChild(dept: Api.SystemManage.Department) {
  handleDeleteDept(dept);
}

async function init() {
  await loadTree();
  loadMembers();
}

init();
</script>

<template>
  <div class="dept-page">
    <!-- 左：部门结构树 -->
    <aside class="dept-page__tree vk-card">
      <div class="dept-page__tree-head">
        <span class="vk-card-title">部门结构</span>
        <NButton v-if="hasAuth('manage:dept:create')" size="tiny" quaternary type="primary" @click="handleCreateRoot">
          新建根部门
        </NButton>
      </div>
      <div class="dept-page__tree-body">
        <DeptTree ref="treeRef" :selected-id="selectedDeptId" @select="handleSelect" />
      </div>
    </aside>

    <!-- 右：部门详情 -->
    <section v-if="selectedDept" class="dept-page__main">
      <!-- 部门信息编辑卡 -->
      <div class="vk-card dept-page__info">
        <div class="dept-page__info-head">
          <span class="vk-card-title">{{ selectedDept.name }}</span>
          <span class="dept-page__path">路径：{{ selectedDept.path || '-' }}</span>
          <NSpace :size="8">
            <NButton v-if="hasAuth('manage:dept:create')" size="small" secondary @click="handleCreateChild">
              新建子部门
            </NButton>
            <NButton
              v-if="hasAuth('manage:dept:delete')"
              size="small"
              secondary
              type="error"
              @click="handleDeleteDept(selectedDept)"
            >
              删除
            </NButton>
          </NSpace>
        </div>
        <NForm inline label-placement="left" :show-feedback="false" class="dept-page__form">
          <NFormItem label="名称">
            <NInput v-model:value="deptForm.name" placeholder="部门名称" class="w-200px" />
          </NFormItem>
          <NFormItem label="排序">
            <NInputNumber v-model:value="deptForm.sort" :min="0" class="w-120px" />
          </NFormItem>
          <NFormItem label="状态">
            <NRadioGroup v-model:value="deptForm.status">
              <NRadio :value="1">启用</NRadio>
              <NRadio :value="0">停用</NRadio>
            </NRadioGroup>
          </NFormItem>
          <NFormItem v-if="hasAuth('manage:dept:update')">
            <NButton type="primary" size="small" :loading="saving" @click="handleSaveDept">保存</NButton>
          </NFormItem>
        </NForm>
      </div>

      <!-- 成员列表卡 -->
      <div class="vk-card dept-page__members">
        <div class="dept-page__section-head">
          <span class="vk-section-title">成员（{{ members.length }}）</span>
          <span class="dept-page__hint">展示该部门下成员，可在「用户管理」中调整归属</span>
        </div>
        <NDataTable
          :columns="memberColumns"
          :data="members"
          :loading="memberLoading"
          :row-key="memberRowKey"
          size="small"
          :bordered="false"
          max-height="260"
        />
      </div>

      <!-- 子部门卡 -->
      <div class="vk-card dept-page__children">
        <div class="dept-page__section-head">
          <span class="vk-section-title">子部门（{{ childDepts.length }}）</span>
          <NButton
            v-if="hasAuth('manage:dept:create')"
            size="tiny"
            quaternary
            type="primary"
            @click="handleCreateChild"
          >
            新建子部门
          </NButton>
        </div>
        <div v-if="childDepts.length" class="dept-page__child-list">
          <div v-for="child in childDepts" :key="child.id" class="dept-page__child-row">
            <span class="dept-page__child-name">{{ child.name }}</span>
            <span class="dept-page__child-sort">排序 {{ child.sort }}</span>
            <span class="vk-status" :class="[child.status === 1 ? 'vk-status--success' : 'vk-status--muted']">
              <i class="vk-status__dot" />
              {{ child.status === 1 ? '启用' : '停用' }}
            </span>
            <NSpace :size="4">
              <NButton size="tiny" quaternary @click="selectedDeptId = child.id">查看</NButton>
              <NButton
                v-if="hasAuth('manage:dept:delete')"
                size="tiny"
                quaternary
                type="error"
                @click="handleDeleteChild(child)"
              >
                删除
              </NButton>
            </NSpace>
          </div>
        </div>
        <div v-else class="dept-page__empty">暂无子部门</div>
      </div>
    </section>

    <!-- 未选中部门空态 -->
    <section v-else class="vk-card dept-page__main dept-page__placeholder">
      <NEmpty description="请选择左侧部门查看详情" />
    </section>

    <!-- 新建部门抽屉 -->
    <DeptEditDrawer
      v-model:visible="drawerVisible"
      :parent-id="createParentId"
      :parent-name="createParentName"
      @submitted="handleDrawerSubmitted"
    />
  </div>
</template>

<style scoped>
/* 页面骨架：左树 260px + 右详情列（DESIGN 组织页布局） */
.dept-page {
  display: flex;
  gap: 16px;
  height: 100%;
  min-height: 0;
  padding: 16px;
  overflow: hidden;
}

.vk-card {
  background: var(--vk-paper);
  border: 1px solid var(--vk-line);
  border-radius: var(--vk-radius-card);
}

.vk-card-title {
  font-size: var(--vk-font-title);
  font-weight: 550;
  color: var(--vk-ink);
}

.vk-section-title {
  font-size: var(--vk-font-body);
  font-weight: 550;
  color: var(--vk-ink);
}

/* 左树 */
.dept-page__tree {
  flex: none;
  width: 260px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.dept-page__tree-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 12px 8px 16px;
}

.dept-page__tree-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 8px 12px;
}

/* 右侧详情列 */
.dept-page__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.dept-page__info {
  padding: 16px;
}

.dept-page__info-head {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.dept-page__path {
  flex: 1;
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
  font-variant-numeric: tabular-nums;
}

.dept-page__form {
  flex-wrap: wrap;
  row-gap: 12px;
}

.dept-page__members,
.dept-page__children {
  padding: 16px;
}

.dept-page__section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.dept-page__hint {
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
}

/* 表格：表头浅底次文字（DESIGN 数据表规格） */
.dept-page :deep(.n-data-table .n-data-table-th) {
  background: var(--vk-soft);
  color: var(--vk-muted);
  font-size: var(--vk-font-caption);
}

.dept-page :deep(.n-data-table .n-data-table-td) {
  font-size: var(--vk-font-dense);
}

/* 子部门行列表 */
.dept-page__child-list {
  display: flex;
  flex-direction: column;
}

.dept-page__child-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 4px;
  border-bottom: 1px solid var(--vk-line);
  font-size: var(--vk-font-dense);
}

.dept-page__child-row:last-child {
  border-bottom: none;
}

.dept-page__child-name {
  flex: 1;
  color: var(--vk-ink);
}

.dept-page__child-sort {
  color: var(--vk-muted);
  font-size: var(--vk-font-caption);
  font-variant-numeric: tabular-nums;
}

.dept-page__empty {
  padding: 20px 0;
  text-align: center;
  color: var(--vk-muted);
  font-size: var(--vk-font-caption);
}

.dept-page__placeholder {
  align-items: center;
  justify-content: center;
  display: flex;
}

/* 状态标签：圆点 + 文字 */
.vk-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--vk-font-dense);
  border-radius: var(--vk-radius-micro);
  padding: 2px 8px;
}

.vk-status__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.vk-status--success {
  color: var(--vk-success-ink);
  background: var(--vk-green-soft);
}

.vk-status--success .vk-status__dot {
  background: var(--vk-green);
}

.vk-status--muted {
  color: var(--vk-muted);
  background: var(--vk-soft);
}

.vk-status--muted .vk-status__dot {
  background: var(--vk-muted);
}

.vk-role-tag {
  display: inline-block;
  font-size: var(--vk-font-caption);
  color: var(--vk-ink);
  background: var(--vk-soft);
  border-radius: var(--vk-radius-micro);
  padding: 1px 8px;
  line-height: 18px;
  white-space: nowrap;
}

.vk-muted-text {
  color: var(--vk-muted);
  font-size: var(--vk-font-dense);
}

/* ≤760px：树与详情纵排（DESIGN 响应式规格） */
@media (max-width: 760px) {
  .dept-page {
    flex-direction: column;
    overflow-y: auto;
  }

  .dept-page__tree {
    width: 100%;
    max-height: 260px;
  }
}
</style>
