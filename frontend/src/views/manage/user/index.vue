<script setup lang="tsx">
import { computed, onMounted, reactive, ref } from 'vue';
import { NButton, NSpace } from 'naive-ui';
import { useLoading } from '@sa/hooks';
import { fetchGetRoles, fetchGetUsers, fetchResetUserPassword, fetchUpdateUserStatus } from '@/service/api';
import { useAuth } from '@/hooks/business/auth';
import DeptTree from '../components/dept-tree.vue';
import UserOperateDrawer from './modules/user-operate-drawer.vue';

/**
 * 用户管理（Phase 5 Task 3，DESIGN：左部门树 260px + 右成员表）
 *
 * - 左侧部门树选中 → 表格按 dept_id 过滤；「全部成员」根节点取消过滤
 * - 操作按钮按权限码显隐：manage:user:create/update/status/reset_password
 * - 重置密码：确认对话框 → 展示一次性临时密码（复制 + 妥善保管提示）
 */

const { hasAuth } = useAuth();
const { loading, startLoading, endLoading } = useLoading();

// 搜索参数（dept_id 由左侧树选中驱动）
const searchParams = reactive({
  current: 1,
  pageSize: 10,
  keyword: '',
  role: null as string | null,
  status: null as number | null,
  dept_id: null as string | null
});

const data = ref<Api.SystemManage.User[]>([]);
const total = ref(0);

// 部门树选中（null = 全部成员）
const selectedDeptId = ref<string | null>(null);

// 角色选项与编码 → 名称映射（列表角色标签用）
const roleOptions = ref<{ label: string; value: string }[]>([]);
const roleNameMap = ref<Record<string, string>>({});

async function loadRoles() {
  const { error, data: roles } = await fetchGetRoles();
  if (!error && roles) {
    roleOptions.value = roles.map(r => ({ label: r.label, value: r.value }));
    roleNameMap.value = Object.fromEntries(roles.map(r => [r.value, r.label]));
  }
}

async function loadUsers() {
  startLoading();
  const { error, data: resp } = await fetchGetUsers({
    current: searchParams.current,
    pageSize: searchParams.pageSize,
    keyword: searchParams.keyword || null,
    role: searchParams.role,
    status: searchParams.status,
    dept_id: searchParams.dept_id
  });
  if (!error && resp) {
    data.value = resp.rows;
    total.value = resp.total;
  } else {
    window.$message?.error('加载用户列表失败');
  }
  endLoading();
}

// 关键字防抖（300ms）
let keywordTimer: ReturnType<typeof setTimeout> | null = null;
function handleKeywordUpdate(value: string) {
  searchParams.keyword = value;
  if (keywordTimer) clearTimeout(keywordTimer);
  keywordTimer = setTimeout(() => {
    searchParams.current = 1;
    loadUsers();
  }, 300);
}

function handleFilterChange() {
  searchParams.current = 1;
  loadUsers();
}

// 左侧树选中部门 → 重置页码并过滤
function handleDeptSelect(deptId: string | null) {
  searchParams.dept_id = deptId;
  searchParams.current = 1;
  loadUsers();
}

// 状态标签：圆点 + 文字（DESIGN 状态标签规格）
function renderStatus(enabled: boolean) {
  return (
    <span class={`vk-status ${enabled ? 'vk-status--success' : 'vk-status--muted'}`}>
      <i class="vk-status__dot" />
      {enabled ? '启用' : '禁用'}
    </span>
  );
}

// 角色编码列表：优先 roleCodes（user_role），存量用户回退 role 字符串
function getRoleCodes(row: Api.SystemManage.User): string[] {
  if (row.roleCodes?.length) return row.roleCodes;
  if (row.role) return [row.role];
  return [];
}

// 角色标签：无角色显示 muted 占位
function renderRoles(row: Api.SystemManage.User, roleMap: Record<string, string>) {
  const codes = getRoleCodes(row);
  if (!codes.length) {
    return <span class="vk-muted-text">未分配</span>;
  }
  return (
    <NSpace size={4} wrap={false} align="center">
      {codes.map(code => (
        <span key={code} class="vk-role-tag">
          {roleMap[code] || code}
        </span>
      ))}
    </NSpace>
  );
}

const columns = computed(() => {
  // 引用 roleNameMap 使 computed 依赖角色映射：角色异步加载完成后列重新生成
  const roleMap = roleNameMap.value;
  return [
    {
      key: 'username',
      title: '账号',
      width: 140,
      render: (row: Api.SystemManage.User) => row.username || row.ssoAccount || '-'
    },
    {
      key: 'name',
      title: '姓名',
      width: 130,
      render: (row: Api.SystemManage.User) => row.name || row.ssoName || '-'
    },
    {
      key: 'roles',
      title: '角色',
      minWidth: 160,
      render: (row: Api.SystemManage.User) => renderRoles(row, roleMap)
    },
    {
      key: 'status',
      title: '状态',
      width: 90,
      render: (row: Api.SystemManage.User) => renderStatus(row.status === 1)
    },
    {
      key: 'lastLoginTime',
      title: '最后登录',
      width: 170,
      render: (row: Api.SystemManage.User) =>
        row.lastLoginTime ? new Date(row.lastLoginTime).toLocaleString('zh-CN') : '从未登录'
    },
    {
      key: 'actions',
      title: '操作',
      width: 230,
      render: (row: Api.SystemManage.User) => {
        const actions: JSX.Element[] = [];
        if (hasAuth('manage:user:update')) {
          actions.push(
            <NButton size="tiny" quaternary onClick={() => handleEdit(row)}>
              编辑
            </NButton>
          );
        }
        if (hasAuth('manage:user:reset_password')) {
          actions.push(
            <NButton size="tiny" quaternary onClick={() => handleResetPassword(row)}>
              重置密码
            </NButton>
          );
        }
        if (hasAuth('manage:user:status')) {
          actions.push(
            <NButton size="tiny" quaternary onClick={() => handleToggleStatus(row)}>
              {row.status === 1 ? '禁用' : '启用'}
            </NButton>
          );
        }
        return <NSpace size={4}>{actions}</NSpace>;
      }
    }
  ];
});

function rowKey(row: Api.SystemManage.User) {
  return row.id;
}

function handlePageChange(current: number) {
  searchParams.current = current;
  loadUsers();
}

function handlePageSizeChange(pageSize: number) {
  searchParams.pageSize = pageSize;
  searchParams.current = 1;
  loadUsers();
}

// ===== 新建 / 编辑抽屉 =====
const drawerVisible = ref(false);
const editingUserId = ref<string | null>(null);

function handleCreate() {
  editingUserId.value = null;
  drawerVisible.value = true;
}

function handleEdit(row: Api.SystemManage.User) {
  editingUserId.value = row.id;
  drawerVisible.value = true;
}

function handleDrawerSubmitted() {
  searchParams.current = 1;
  loadUsers();
}

// ===== 禁用 / 启用 =====
function handleToggleStatus(row: Api.SystemManage.User) {
  const disabling = row.status === 1;
  window.$dialog?.warning({
    title: disabling ? '禁用用户' : '启用用户',
    content: disabling
      ? `确认禁用 ${row.name || row.username || row.ssoAccount} 吗？禁用后该用户将无法访问系统。`
      : `确认启用 ${row.name || row.username || row.ssoAccount} 吗？`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      const { error } = await fetchUpdateUserStatus(row.id, { status: disabling ? 0 : 1 });
      if (!error) {
        window.$message?.success(disabling ? '已禁用' : '已启用');
        loadUsers();
      } else {
        window.$message?.error('状态更新失败');
      }
    }
  });
}

// ===== 重置密码：确认 → 一次性临时密码 =====
const tempPasswordVisible = ref(false);
const tempPassword = ref('');
const tempPasswordOwner = ref('');

function handleResetPassword(row: Api.SystemManage.User) {
  window.$dialog?.warning({
    title: '重置密码',
    content: `确认重置 ${row.name || row.username || row.ssoAccount} 的密码吗？重置后该用户的当前登录会话将全部失效。`,
    positiveText: '确认重置',
    negativeText: '取消',
    onPositiveClick: async () => {
      const { error, data: resp } = await fetchResetUserPassword(row.id);
      if (!error && resp) {
        tempPassword.value = resp.tempPassword;
        tempPasswordOwner.value = row.username || row.ssoAccount || '';
        tempPasswordVisible.value = true;
      } else {
        window.$message?.error('重置密码失败');
      }
    }
  });
}

async function copyTempPassword() {
  try {
    await navigator.clipboard.writeText(tempPassword.value);
    window.$message?.success('已复制到剪贴板');
  } catch {
    // 剪贴板 API 不可用时退回选区复制
    const input = document.createElement('textarea');
    input.value = tempPassword.value;
    document.body.appendChild(input);
    input.select();
    document.execCommand('copy');
    document.body.removeChild(input);
    window.$message?.success('已复制到剪贴板');
  }
}

onMounted(() => {
  loadRoles();
  loadUsers();
});
</script>

<template>
  <div class="user-page">
    <!-- 左：部门树（默认 260px；≤760px 纵排） -->
    <aside class="user-page__tree vk-card">
      <div class="user-page__tree-head">
        <span class="vk-card-title">部门</span>
      </div>
      <div class="user-page__tree-body">
        <DeptTree show-all all-label="全部成员" :selected-id="selectedDeptId" @select="handleDeptSelect" />
      </div>
    </aside>

    <!-- 右：成员表格卡 -->
    <section class="user-page__main vk-card">
      <div class="user-page__toolbar">
        <div class="user-page__filters">
          <NInput
            :value="searchParams.keyword"
            placeholder="搜索账号或姓名"
            clearable
            size="small"
            class="user-page__search"
            @update:value="handleKeywordUpdate"
          />
          <NSelect
            v-model:value="searchParams.role"
            :options="roleOptions"
            placeholder="全部角色"
            clearable
            size="small"
            class="user-page__select"
            @update:value="handleFilterChange"
          />
          <NSelect
            v-model:value="searchParams.status"
            :options="[
              { label: '启用', value: 1 },
              { label: '禁用', value: 0 }
            ]"
            placeholder="全部状态"
            clearable
            size="small"
            class="user-page__select user-page__select--status"
            @update:value="handleFilterChange"
          />
        </div>
        <NButton v-if="hasAuth('manage:user:create')" type="primary" size="small" @click="handleCreate">
          新建用户
        </NButton>
      </div>

      <div class="user-page__table">
        <NDataTable
          :columns="columns"
          :data="data"
          :loading="loading"
          :row-key="rowKey"
          :pagination="{
            page: searchParams.current,
            pageSize: searchParams.pageSize,
            itemCount: total,
            prefix: ({ itemCount }) => `共 ${itemCount} 人`,
            showSizePicker: true,
            pageSizes: [10, 20, 50],
            onChange: handlePageChange,
            onUpdatePageSize: handlePageSizeChange
          }"
          flex-height
          class="h-full"
        />
      </div>
    </section>

    <!-- 新建 / 编辑用户抽屉 -->
    <UserOperateDrawer v-model:visible="drawerVisible" :user-id="editingUserId" @submitted="handleDrawerSubmitted" />

    <!-- 重置密码结果（临时密码仅展示一次） -->
    <NModal v-model:show="tempPasswordVisible" preset="card" title="密码已重置" class="user-page__temp-modal">
      <div class="user-page__temp-body">
        <p class="user-page__temp-tip">
          <code>{{ tempPasswordOwner }}</code>
          的临时密码：
        </p>
        <div class="user-page__temp-pass">
          <span class="user-page__temp-value">{{ tempPassword }}</span>
          <NButton size="tiny" secondary @click="copyTempPassword">复制</NButton>
        </div>
        <p class="user-page__temp-warn">临时密码仅显示这一次，请复制并妥善转告用户；用户首次登录时需要修改密码。</p>
      </div>
      <template #footer>
        <div class="user-page__temp-footer">
          <NButton type="primary" size="small" @click="tempPasswordVisible = false">我已妥善保管</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
/* 页面骨架：左树 260px + 右表格卡（DESIGN 组织页布局） */
.user-page {
  display: flex;
  gap: 16px;
  height: 100%;
  min-height: 0;
  padding: 16px;
  overflow: hidden;
}

/* 卡片：paper + 1px line + 16px 圆角，常态无阴影 */
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

/* 左树 */
.user-page__tree {
  flex: none;
  width: 260px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.user-page__tree-head {
  padding: 14px 16px 8px;
}

.user-page__tree-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 8px 12px;
}

/* 右侧主卡 */
.user-page__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 16px;
}

.user-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.user-page__filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.user-page__search {
  width: 200px;
}

.user-page__select {
  width: 140px;
}

.user-page__select--status {
  width: 110px;
}

.user-page__table {
  flex: 1;
  min-height: 0;
}

/* 表格：表头浅底次文字，行悬停 bg（DESIGN 数据表规格） */
.user-page :deep(.n-data-table .n-data-table-th) {
  background: var(--vk-soft);
  color: var(--vk-muted);
  font-size: var(--vk-font-caption);
}

.user-page :deep(.n-data-table .n-data-table-td) {
  font-size: var(--vk-font-dense);
}

/* 状态标签：圆点 + 文字（5px 圆角小标签） */
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

/* 角色标签：soft 底小胶囊 */
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

/* 临时密码弹窗 */
.user-page__temp-modal {
  width: 460px;
  border-radius: var(--vk-radius-dialog);
}

.user-page__temp-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-page__temp-tip {
  margin: 0;
  color: var(--vk-ink);
}

.user-page__temp-pass {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--vk-soft);
  border: 1px solid var(--vk-line);
  border-radius: var(--vk-radius-control);
  padding: 10px 12px;
}

.user-page__temp-value {
  font-size: 16px;
  letter-spacing: 1px;
  color: var(--vk-ink);
  font-variant-numeric: tabular-nums;
}

.user-page__temp-warn {
  margin: 0;
  font-size: var(--vk-font-caption);
  color: var(--vk-warning-ink);
  background: var(--vk-warning-soft);
  border-radius: var(--vk-radius-micro);
  padding: 6px 10px;
}

.user-page__temp-footer {
  display: flex;
  justify-content: flex-end;
}

/* ≤760px：树与表格纵排，树区限高内部滚动（DESIGN 响应式规格） */
@media (max-width: 760px) {
  .user-page {
    flex-direction: column;
    overflow-y: auto;
  }

  .user-page__tree {
    width: 100%;
    max-height: 260px;
  }

  .user-page__main {
    min-height: 420px;
  }
}
</style>
