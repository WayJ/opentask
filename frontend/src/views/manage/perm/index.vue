<script setup lang="tsx">
import { ref } from 'vue';
import { NSwitch, NTag } from 'naive-ui';
import { fetchGetPermissions, fetchUpdatePermissionStatus } from '@/service/api';
import { useAuth } from '@/hooks/business/auth';

/**
 * 权限点管理（Phase 5 Task 4）
 *
 * 权限点字典由代码定义（后端 permission_defs.py + seed 幂等同步），
 * 本页只读展示 + 启停开关；停用后 require_permission 即时 403。
 */

defineOptions({ name: 'ManagePerm' });

const { hasAuth } = useAuth();

const canToggle = hasAuth('manage:role:perm');

const permissions = ref<Api.SystemManage.PermissionInfo[]>([]);
const loading = ref(false);
const togglingIds = ref<string[]>([]);

async function loadPermissions() {
  loading.value = true;
  const { error, data } = await fetchGetPermissions();
  loading.value = false;
  if (!error && data) {
    permissions.value = data;
  }
}

async function handleToggle(row: Api.SystemManage.PermissionInfo, value: boolean) {
  const status = value ? 1 : 0;
  togglingIds.value.push(row.id);
  const { error } = await fetchUpdatePermissionStatus(row.id, status as 0 | 1);
  togglingIds.value = togglingIds.value.filter(id => id !== row.id);
  if (!error) {
    row.status = status;
    window.$message?.success(value ? `已启用 ${row.code}` : `已停用 ${row.code}`);
  }
}

function rowKey(row: Api.SystemManage.PermissionInfo) {
  return row.id;
}

const columns = [
  {
    key: 'code',
    title: '权限码',
    minWidth: 220,
    render: (row: Api.SystemManage.PermissionInfo) => <span class="vk-mono-code">{row.code}</span>
  },
  {
    key: 'name',
    title: '名称',
    minWidth: 140,
    render: (row: Api.SystemManage.PermissionInfo) => row.name || '-'
  },
  {
    key: 'type',
    title: '类型',
    width: 90,
    render: (row: Api.SystemManage.PermissionInfo) => (
      <NTag size="small" bordered={false} type={row.type === 'menu' ? 'info' : 'default'}>
        {row.type === 'menu' ? '菜单' : '按钮'}
      </NTag>
    )
  },
  {
    key: 'route_key',
    title: '关联路由',
    minWidth: 140,
    render: (row: Api.SystemManage.PermissionInfo) => row.route_key || '-'
  },
  {
    key: 'status',
    title: '状态',
    width: 110,
    render: (row: Api.SystemManage.PermissionInfo) => (
      <span class={`vk-status ${row.status === 1 ? 'vk-status--success' : 'vk-status--muted'}`}>
        <i class="vk-status__dot" />
        {row.status === 1 ? '启用' : '停用'}
      </span>
    )
  },
  {
    key: 'operate',
    title: '启停',
    width: 90,
    render: (row: Api.SystemManage.PermissionInfo) => (
      <NSwitch
        value={row.status === 1}
        size="small"
        disabled={!canToggle || togglingIds.value.includes(row.id)}
        onUpdateValue={(value: boolean) => handleToggle(row, value)}
      />
    )
  }
];

loadPermissions();
</script>

<template>
  <div class="perm-page">
    <!-- 提示条：字典只读，仅可启停 -->
    <NAlert type="info" :show-icon="true" :bordered="false" class="perm-page__tip">
      权限点字典由代码定义并自动同步，此处仅可启停；停用后依赖该权限码的接口与入口立即失效。
    </NAlert>

    <div class="vk-card perm-page__table">
      <div class="perm-page__head">
        <span class="vk-card-title">权限点</span>
        <span class="perm-page__count">共 {{ permissions.length }} 项</span>
      </div>
      <NDataTable
        :columns="columns"
        :data="permissions"
        :loading="loading"
        :row-key="rowKey"
        size="small"
        :bordered="false"
        max-height="calc(100vh - 260px)"
      />
    </div>
  </div>
</template>

<style scoped>
.perm-page {
  display: flex;
  flex-direction: column;
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

.perm-page__tip {
  border-radius: var(--vk-radius-card);
}

.perm-page__table {
  flex: 1;
  min-height: 0;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.perm-page__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.perm-page__count {
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
  font-variant-numeric: tabular-nums;
}

/* 表格：表头浅底次文字（DESIGN 数据表规格） */
.perm-page :deep(.n-data-table .n-data-table-th) {
  background: var(--vk-soft);
  color: var(--vk-muted);
  font-size: var(--vk-font-caption);
}

.perm-page :deep(.n-data-table .n-data-table-td) {
  font-size: var(--vk-font-dense);
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

.vk-mono-code {
  font-variant-numeric: tabular-nums;
  color: var(--vk-ink);
}

/* ≤760px：放开高度纵排滚动 */
@media (max-width: 760px) {
  .perm-page {
    overflow-y: auto;
    height: auto;
    min-height: 100%;
  }
}
</style>
