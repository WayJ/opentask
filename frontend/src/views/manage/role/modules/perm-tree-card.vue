<script setup lang="ts">
import { computed, h, ref, watch } from 'vue';
import type { TreeOption } from 'naive-ui';
import { fetchGetPermissions, fetchSetRolePermissions } from '@/service/api';

/**
 * 功能权限卡（角色详情 CARD 2）
 *
 * - GET /api/permissions 按 code 前缀分组（menu / manage:user / requirement 等）成树勾选；
 * - 勾选集由父组件回显（initialCodes = GET /api/roles/{id}/permissions 的 codes）；
 * - 保存整组 PUT codes；停用权限点禁选（后端会拒绝停用码）；
 * - admin 角色持有全量权限且后端 409，树禁用 + 提示。
 */

defineOptions({ name: 'PermTreeCard' });

interface Props {
  roleId: string;
  roleCode: string;
  initialCodes: string[];
  /** 父组件回显请求完成后再渲染勾选，避免先渲染空树再闪变 */
  detailLoaded: boolean;
}

const props = defineProps<Props>();

interface Emits {
  (e: 'saved', codes: string[]): void;
}

const emit = defineEmits<Emits>();

// 分组标签（未知前缀回退显示前缀本身）
const GROUP_LABELS: Record<string, string> = {
  menu: '管理端菜单',
  'manage:user': '用户管理',
  'manage:dept': '部门管理',
  'manage:role': '角色管理',
  'manage:dingtalk': '钉钉同步',
  requirement: '需求',
  issue: '问题',
  project: '项目',
  knowledge: '知识库',
  task: '任务',
  profile: '个人中心'
};

/** 分组键：manage:* 取前两段，其余取第一段 */
function groupKey(code: string): string {
  const seg = code.split(':');
  if (seg[0] === 'manage') return `manage:${seg[1]}`;
  return seg[0];
}

const permissions = ref<Api.SystemManage.PermissionInfo[]>([]);
const permLoading = ref(false);
const checkedKeys = ref<string[]>([]);
const saving = ref(false);

// code → 是否启用（停用权限点禁选）
const enabledMap = computed(() => {
  const map: Record<string, boolean> = {};
  permissions.value.forEach(p => {
    map[p.code] = p.status === 1;
  });
  return map;
});

// admin 角色：全量权限后端下发且不可改
const isAdminRole = computed(() => props.roleCode === 'admin');

const permTreeData = computed<TreeOption[]>(() => {
  const groups = new Map<string, Api.SystemManage.PermissionInfo[]>();
  permissions.value.forEach(p => {
    const key = groupKey(p.code);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(p);
  });
  return [...groups.entries()].map(([key, perms]) => ({
    key: `group:${key}`,
    label: GROUP_LABELS[key] || key,
    children: perms.map(p => ({
      key: p.code,
      label: p.name,
      disabled: !enabledMap.value[p.code] || isAdminRole.value,
      // 停用权限点在名称后标注，避免"为什么不能勾选"的困惑
      suffix: () =>
        p.status === 1
          ? null
          : h('span', { style: 'font-size:10px;color:var(--vk-muted);margin-left:6px' }, '（已停用）')
    }))
  }));
});

async function loadPermissions() {
  permLoading.value = true;
  const { error, data } = await fetchGetPermissions();
  permLoading.value = false;
  if (!error && data) {
    permissions.value = data;
  }
}

// 角色切换时同步勾选集（树数据与勾选都就绪后）
watch(
  () => [props.roleId, props.detailLoaded] as const,
  ([, loaded]) => {
    if (loaded) {
      checkedKeys.value = [...props.initialCodes];
    }
  },
  { immediate: true }
);

// 已选权限码集合（仅保留真实存在的权限码，过滤分组键）
const selectedCodes = computed(() => checkedKeys.value.filter(key => key in enabledMap.value));

async function handleSave() {
  // 后端拒绝停用权限码：提交前剔除
  const codes = selectedCodes.value.filter(code => enabledMap.value[code]);
  saving.value = true;
  const { error } = await fetchSetRolePermissions(props.roleId, codes);
  saving.value = false;
  if (!error) {
    window.$message?.success('功能权限已保存');
    emit('saved', codes);
  }
}

loadPermissions();
</script>

<template>
  <div class="vk-card perm-card">
    <div class="perm-card__head">
      <span class="perm-card__title">功能权限</span>
      <span class="perm-card__hint">
        {{ isAdminRole ? 'admin 角色持有全量权限，不可修改' : '按模块分组勾选，保存后整组覆盖' }}
      </span>
      <NButton type="primary" size="small" :loading="saving" :disabled="isAdminRole" @click="handleSave">
        保存权限
      </NButton>
    </div>
    <NAlert v-if="isAdminRole" type="warning" :show-icon="false" class="perm-card__alert">
      系统管理员角色持有全部权限（由系统预置），不允许修改。
    </NAlert>
    <NSpin :show="permLoading" size="small">
      <div class="perm-card__body">
        <NTree
          v-model:checked-keys="checkedKeys"
          :data="permTreeData"
          checkable
          cascade
          :selectable="false"
          block-line
          :default-expanded-keys="permTreeData.map(n => n.key)"
          class="perm-card__tree"
        />
        <div v-if="!permissions.length && !permLoading" class="perm-card__empty">
          暂无权限点（权限字典由后端代码定义并播种）
        </div>
      </div>
    </NSpin>
    <div class="perm-card__foot">已选 {{ selectedCodes.length }} / {{ permissions.length }} 项</div>
  </div>
</template>

<style scoped>
.perm-card {
  padding: 16px;
}

.perm-card__head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.perm-card__title {
  font-size: var(--vk-font-body);
  font-weight: 550;
  color: var(--vk-ink);
}

.perm-card__hint {
  flex: 1;
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
}

.perm-card__alert {
  margin-bottom: 12px;
  border-radius: var(--vk-radius-compact);
}

.perm-card__body {
  border: 1px solid var(--vk-line);
  border-radius: var(--vk-radius-compact);
  background: var(--vk-bg);
  padding: 8px 12px;
  max-height: 320px;
  overflow-y: auto;
  min-height: 80px;
}

.perm-card__tree {
  --n-node-border-radius: 6px;
}

.perm-card__empty {
  padding: 20px 0;
  text-align: center;
  color: var(--vk-muted);
  font-size: var(--vk-font-caption);
}

.perm-card__foot {
  margin-top: 8px;
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
  font-variant-numeric: tabular-nums;
}
</style>
