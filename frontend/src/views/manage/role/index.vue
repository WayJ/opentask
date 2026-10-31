<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import type { TreeOption } from 'naive-ui';
import {
  fetchDeleteRole,
  fetchGetDeptTree,
  fetchGetRolePermissions,
  fetchGetRoles,
  fetchUpdateRole
} from '@/service/api';
import { useAuth } from '@/hooks/business/auth';
import PermTreeCard from './modules/perm-tree-card.vue';
import RoleEditDrawer from './modules/role-edit-drawer.vue';

/**
 * 角色管理（Phase 5 Task 4，DESIGN：左角色列表 235px + 右详情卡）
 *
 * - 右侧三卡：基本信息（name/description + data_scope 分段选择，
 *   CUSTOM 展开部门树多选）/ 功能权限（perm-tree-card）/ 删除（系统角色隐藏）
 * - 系统角色只许改 name/description（data_scope 禁用）；
 *   admin 角色权限由后端全量下发且不可改（树禁用 + 提示）
 */

defineOptions({ name: 'ManageRole' });

const { hasAuth } = useAuth();

// ===== 角色列表（左栏） =====
const roles = ref<Api.SystemManage.RoleInfo[]>([]);
const listLoading = ref(false);
const selectedRoleId = ref<string | null>(null);

const selectedRole = computed(() => roles.value.find(r => r.id === selectedRoleId.value) || null);

async function loadRoles(selectId?: string) {
  listLoading.value = true;
  const { error, data } = await fetchGetRoles();
  listLoading.value = false;
  if (!error && data) {
    roles.value = data;
    if (selectId) {
      selectedRoleId.value = selectId;
    } else if (selectedRoleId.value && !data.some(r => r.id === selectedRoleId.value)) {
      selectedRoleId.value = data[0]?.id || null;
    } else if (!selectedRoleId.value && data.length) {
      selectedRoleId.value = data[0].id;
    }
  }
}

// ===== 数据范围档位（与后端 VALID_DATA_SCOPES 一致） =====
const DATA_SCOPES: { value: Api.SystemManage.DataScope; label: string }[] = [
  { value: 'ALL', label: '全部数据' },
  { value: 'DEPT_AND_CHILD', label: '本部门及子部门' },
  { value: 'DEPT', label: '仅本部门' },
  { value: 'CUSTOM', label: '自定义部门' },
  { value: 'SELF', label: '仅本人' }
];

// ===== 基本信息编辑 =====
const roleForm = reactive({
  name: '',
  description: '',
  data_scope: 'SELF' as Api.SystemManage.DataScope
});
const saving = ref(false);

// CUSTOM 自定义部门（树多选）
const deptTree = ref<TreeOption[]>([]);
const checkedDeptIds = ref<string[]>([]);
const detailLoaded = ref(false);

// 当前角色权限码（CARD 2 与 CUSTOM 部门回显共用一次请求）
const rolePermissionCodes = ref<string[]>([]);

const isSystem = computed(() => selectedRole.value?.is_system === true);

watch(
  selectedRoleId,
  async id => {
    detailLoaded.value = false;
    if (!id) return;
    const role = selectedRole.value;
    roleForm.name = role?.name || '';
    roleForm.description = role?.description || '';
    roleForm.data_scope = (role?.data_scope || 'SELF') as Api.SystemManage.DataScope;
    checkedDeptIds.value = [];
    rolePermissionCodes.value = [];
    const { error, data } = await fetchGetRolePermissions(id);
    if (!error && data) {
      rolePermissionCodes.value = data.codes;
      checkedDeptIds.value = data.dept_ids;
    }
    detailLoaded.value = true;
  },
  { immediate: false }
);

async function loadDeptTree() {
  const { error, data } = await fetchGetDeptTree();
  if (!error && data) {
    deptTree.value = data.map(toDeptTreeOption);
  }
}

function toDeptTreeOption(node: Api.SystemManage.Department): TreeOption {
  return {
    key: node.id,
    label: node.name,
    children: node.children?.length ? node.children.map(toDeptTreeOption) : undefined
  };
}

async function handleSaveRole() {
  if (!selectedRoleId.value) return;
  if (!roleForm.name.trim()) {
    window.$message?.warning('角色名称不能为空');
    return;
  }
  saving.value = true;
  const payload: Api.SystemManage.RoleUpdate = {
    name: roleForm.name.trim(),
    description: roleForm.description.trim()
  };
  // 系统角色只许改 name/description（后端同规则）
  if (!isSystem.value) {
    payload.data_scope = roleForm.data_scope;
    if (roleForm.data_scope === 'CUSTOM') {
      payload.dept_ids = checkedDeptIds.value;
    }
  }
  const { error } = await fetchUpdateRole(selectedRoleId.value, payload);
  saving.value = false;
  if (!error) {
    window.$message?.success('角色信息已保存');
    loadRoles(selectedRoleId.value);
  }
}

// ===== 删除 =====
// 从 flat request 的 AxiosError 中取后端 detail（409 冲突原因等）
function getErrMsg(err: unknown, fallback: string) {
  const e = err as { response?: { data?: { detail?: string } }; message?: string } | null;
  return e?.response?.data?.detail || e?.message || fallback;
}

function handleDeleteRole() {
  const role = selectedRole.value;
  if (!role) return;
  window.$dialog?.warning({
    title: '删除角色',
    content: `确认删除角色「${role.name}」吗？删除后不可恢复。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      const { error } = await fetchDeleteRole(role.id);
      if (!error) {
        window.$message?.success('角色已删除');
        if (selectedRoleId.value === role.id) {
          selectedRoleId.value = null;
        }
        loadRoles();
      } else {
        // 后端 409：系统角色 / 角色下仍有用户
        window.$message?.error(getErrMsg(error, '删除失败'));
      }
    }
  });
}

// ===== 新建角色 =====
const drawerVisible = ref(false);

function handleDrawerSubmitted(newRoleId?: string) {
  loadRoles(newRoleId || undefined);
}

async function init() {
  await loadRoles();
  loadDeptTree();
}

init();
</script>

<template>
  <div class="role-page">
    <!-- 左：角色列表（235px） -->
    <aside class="role-page__list vk-card">
      <div class="role-page__list-head">
        <span class="vk-card-title">角色</span>
        <span class="role-page__count">{{ roles.length }}</span>
      </div>
      <NSpin :show="listLoading" size="small">
        <div class="role-page__list-body">
          <button
            v-for="role in roles"
            :key="role.id"
            type="button"
            class="role-page__item"
            :class="{ 'role-page__item--active': role.id === selectedRoleId }"
            @click="selectedRoleId = role.id"
          >
            <span class="role-page__item-name">{{ role.name }}</span>
            <span class="role-page__item-code">{{ role.code }}</span>
            <span v-if="role.is_system" class="role-page__sys-tag">系统</span>
          </button>
          <div v-if="!roles.length && !listLoading" class="role-page__empty">暂无角色</div>
        </div>
      </NSpin>
      <div v-if="hasAuth('manage:role:create')" class="role-page__list-foot">
        <NButton size="small" block @click="drawerVisible = true">新建角色</NButton>
      </div>
    </aside>

    <!-- 右：角色详情 -->
    <section v-if="selectedRole" class="role-page__main">
      <!-- 1. 基本信息 -->
      <div class="vk-card role-page__info">
        <div class="role-page__info-head">
          <span class="vk-card-title">{{ selectedRole.name }}</span>
          <span class="role-page__code">编码：{{ selectedRole.code }}</span>
          <span v-if="selectedRole.is_system" class="role-page__sys-tag">系统角色</span>
        </div>
        <NForm label-placement="top" class="role-page__form" :show-feedback="false">
          <div class="role-page__form-row">
            <NFormItem label="角色名称">
              <NInput v-model:value="roleForm.name" placeholder="角色名称" class="w-240px" />
            </NFormItem>
            <NFormItem label="角色描述">
              <NInput
                v-model:value="roleForm.description"
                placeholder="角色用途说明"
                class="w-360px"
                :maxlength="255"
              />
            </NFormItem>
          </div>
          <NFormItem label="数据范围">
            <NRadioGroup v-model:value="roleForm.data_scope" :disabled="isSystem" name="data-scope">
              <NRadio v-for="scope in DATA_SCOPES" :key="scope.value" :value="scope.value">
                {{ scope.label }}
              </NRadio>
            </NRadioGroup>
          </NFormItem>
          <NFormItem v-if="isSystem" label=" ">
            <span class="role-page__hint">系统角色的数据范围由系统预置，不可修改</span>
          </NFormItem>
          <NFormItem v-if="roleForm.data_scope === 'CUSTOM'" label="自定义部门（多选）">
            <div class="role-page__dept-tree">
              <NTree
                v-model:checked-keys="checkedDeptIds"
                :data="deptTree"
                checkable
                cascade
                :selectable="false"
                block-line
                :virtual-scroll="false"
                class="role-page__dept-tree-inner"
              />
            </div>
          </NFormItem>
          <NFormItem v-if="hasAuth('manage:role:update')">
            <NButton type="primary" size="small" :loading="saving" @click="handleSaveRole">保存基本信息</NButton>
          </NFormItem>
        </NForm>
      </div>

      <!-- 2. 功能权限 -->
      <PermTreeCard
        v-if="hasAuth('manage:role:perm')"
        :role-id="selectedRole.id"
        :role-code="selectedRole.code"
        :initial-codes="rolePermissionCodes"
        :detail-loaded="detailLoaded"
      />

      <!-- 3. 删除（系统角色隐藏） -->
      <div v-if="!selectedRole.is_system && hasAuth('manage:role:delete')" class="vk-card role-page__danger">
        <div class="role-page__danger-text">
          <span class="vk-section-title">删除角色</span>
          <span class="role-page__hint">删除后不可恢复；角色下仍有用户时后端将拒绝删除</span>
        </div>
        <NButton size="small" secondary type="error" @click="handleDeleteRole">删除</NButton>
      </div>
    </section>

    <!-- 未选中角色空态 -->
    <section v-else class="vk-card role-page__main role-page__placeholder">
      <NEmpty description="请选择左侧角色查看详情" />
    </section>

    <!-- 新建角色抽屉 -->
    <RoleEditDrawer v-model:visible="drawerVisible" @submitted="handleDrawerSubmitted" />
  </div>
</template>

<style scoped>
/* 页面骨架：左角色列表 235px + 右详情列（DESIGN 角色页布局） */
.role-page {
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

.role-page__hint {
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
}

/* 左栏角色列表 */
.role-page__list {
  flex: none;
  width: 235px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.role-page__list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 8px;
}

.role-page__count {
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
  font-variant-numeric: tabular-nums;
}

.role-page__list-body {
  flex: 1;
  min-height: 200px;
  overflow-y: auto;
  padding: 4px 8px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* 角色条目：选中 accent-soft 底 + accent-ink 字（DESIGN 选中规格） */
.role-page__item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: var(--vk-radius-control);
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: background-color 0.15s var(--vk-ease);
}

.role-page__item:hover {
  background: var(--vk-soft);
}

.role-page__item--active,
.role-page__item--active:hover {
  background: var(--vk-accent-soft);
}

.role-page__item-name {
  flex: none;
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--vk-font-dense);
  color: var(--vk-ink);
}

.role-page__item--active .role-page__item-name {
  color: var(--vk-accent-ink);
  font-weight: 500;
}

.role-page__item-code {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--vk-font-micro);
  color: var(--vk-muted);
  font-variant-numeric: tabular-nums;
}

.role-page__item--active .role-page__item-code {
  color: var(--vk-accent-ink);
}

.role-page__sys-tag {
  flex: none;
  font-size: var(--vk-font-micro);
  line-height: 16px;
  padding: 0 6px;
  border-radius: var(--vk-radius-micro);
  color: var(--vk-warning-ink);
  background: var(--vk-warning-soft);
}

.role-page__list-foot {
  padding: 10px 12px 12px;
  border-top: 1px solid var(--vk-line);
}

.role-page__empty {
  padding: 20px 0;
  text-align: center;
  color: var(--vk-muted);
  font-size: var(--vk-font-caption);
}

/* 右侧详情列 */
.role-page__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.role-page__info,
.role-page__danger {
  padding: 16px;
}

.role-page__info-head {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.role-page__code {
  flex: 1;
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
  font-variant-numeric: tabular-nums;
}

.role-page__form :deep(.n-form-item) {
  margin-bottom: 14px;
}

.role-page__form-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

/* CUSTOM 部门树：内嵌浅底区域 */
.role-page__dept-tree {
  width: 100%;
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid var(--vk-line);
  border-radius: var(--vk-radius-compact);
  background: var(--vk-bg);
  padding: 8px;
}

.role-page__dept-tree-inner {
  --n-node-border-radius: 6px;
}

/* 删除卡：错误语义浅底 */
.role-page__danger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-color: var(--vk-error-soft);
}

.role-page__danger-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.role-page__placeholder {
  align-items: center;
  justify-content: center;
  display: flex;
}

/* ≤760px：列表与详情纵排（DESIGN 响应式规格） */
@media (max-width: 760px) {
  .role-page {
    flex-direction: column;
    overflow-y: auto;
  }

  .role-page__list {
    width: 100%;
    max-height: 260px;
  }
}
</style>
