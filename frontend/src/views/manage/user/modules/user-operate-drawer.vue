<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { FormInst, FormRules } from 'naive-ui';
import { useLoading } from '@sa/hooks';
import { fetchCreateUser, fetchGetDeptTree, fetchGetRoles, fetchGetUserDetail, fetchUpdateUser } from '@/service/api';

/**
 * 新建 / 编辑用户抽屉
 *
 * - username 编辑时禁改（唯一标识）
 * - 角色多选（/api/roles）、部门多选（树选择）+ 主部门单选（已选部门范围内）
 * - 密码仅新建可填，可留空：留空则账号无初始密码，首次登录需管理员重置/用户改密
 */

interface Props {
  /** 编辑的用户 id；null = 新建 */
  userId?: string | null;
}

const props = withDefaults(defineProps<Props>(), {
  userId: null
});

interface Emits {
  (e: 'update:visible', value: boolean): void;
  (e: 'submitted'): void;
}

const emit = defineEmits<Emits>();

const visible = defineModel<boolean>('visible', {
  default: false
});

const { loading: submitLoading, startLoading, endLoading } = useLoading();

const formRef = ref<FormInst | null>(null);

const isEdit = computed(() => Boolean(props.userId));

interface FormModel {
  username: string;
  name: string;
  roleCodes: string[];
  deptIds: string[];
  primaryDeptId: string | null;
  /** 各部门归属行的岗位 id（编辑回显透传，防止覆盖式保存清岗位） */
  deptPositions: Record<string, string | null>;
  password: string;
}

function createDefaultModel(): FormModel {
  return {
    username: '',
    name: '',
    roleCodes: [],
    deptIds: [],
    primaryDeptId: null,
    deptPositions: {},
    password: ''
  };
}

const model = ref<FormModel>(createDefaultModel());

const rules: FormRules = {
  username: [{ required: true, message: '请输入登录账号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [
    {
      validator: (_rule, value: string) => !value || value.length >= 8,
      message: '密码至少 8 位',
      trigger: 'blur'
    }
  ]
};

// 角色选项
const roleOptions = ref<{ label: string; value: string }[]>([]);

async function loadRoles() {
  const { error, data } = await fetchGetRoles();
  if (!error && data) {
    roleOptions.value = data.map(r => ({ label: r.label, value: r.value }));
  }
}

// 部门树选项（NTreeSelect multiple）
const deptOptions = ref<Api.SystemManage.Department[]>([]);
const deptNameMap = ref<Record<string, string>>({});

function flattenNames(nodes: Api.SystemManage.Department[], acc: Record<string, string> = {}) {
  nodes.forEach(node => {
    acc[node.id] = node.name;
    if (node.children?.length) flattenNames(node.children, acc);
  });
  return acc;
}

async function loadDeptOptions() {
  const { error, data } = await fetchGetDeptTree();
  if (!error && data) {
    deptOptions.value = data;
    deptNameMap.value = flattenNames(data);
  }
}

// 主部门单选选项 = 当前已勾选部门
const primaryOptions = computed(() =>
  model.value.deptIds.map(id => ({ label: deptNameMap.value[id] || id, value: id }))
);

// 部门勾选变化：主部门为空或不在勾选范围内时自动落到第一个
// （首次勾选时 primaryDeptId 为 null，也必须落位，否则提交全 is_primary=false 被后端 400 拒绝）
function handleDeptIdsChange(ids: string[]) {
  model.value.deptIds = ids;
  if (!ids.length || !model.value.primaryDeptId || !ids.includes(model.value.primaryDeptId)) {
    model.value.primaryDeptId = ids[0] || null;
  }
}

// 编辑回显（role_codes + dept_assignments 全量拉取，避免覆盖式保存丢数据）。
// detailLoaded = false 时禁用提交：详情拉不下来就保存会用空角色/部门覆盖清空既有数据。
const detailLoaded = ref(false);

async function loadDetail() {
  if (!props.userId) return;
  detailLoaded.value = false;
  const { error, data } = await fetchGetUserDetail(props.userId);
  if (!error && data) {
    const primary = data.dept_assignments.find(item => item.is_primary);
    model.value = {
      username: data.username || '',
      name: data.name || '',
      roleCodes: data.role_codes || [],
      deptIds: data.dept_assignments.map(item => item.dept_id),
      primaryDeptId: primary?.dept_id || data.dept_assignments[0]?.dept_id || null,
      deptPositions: Object.fromEntries(data.dept_assignments.map(item => [item.dept_id, item.position_id ?? null])),
      password: ''
    };
    detailLoaded.value = true;
  } else {
    window.$message?.error('加载用户详情失败，已禁用保存：请关闭重试，避免清空该用户的角色与部门');
  }
}

function handleInit() {
  model.value = createDefaultModel();
  detailLoaded.value = false;
  formRef.value?.restoreValidation();
  loadRoles();
  loadDeptOptions();
  if (props.userId) {
    loadDetail();
  }
}

watch(visible, value => {
  if (value) {
    handleInit();
  }
});

function closeDrawer() {
  visible.value = false;
}

async function handleSubmit() {
  await formRef.value?.validate();
  // 编辑模式下详情未回显成功则禁止提交（防覆盖式 PUT 清空角色/部门/岗位）
  if (isEdit.value && !detailLoaded.value) {
    window.$message?.error('用户详情尚未加载成功，不能保存');
    return;
  }
  startLoading();
  try {
    // 部门归属载荷：勾选部门逐行映射，主部门标记 is_primary；岗位 id 原样透传
    const deptAssignments: Api.SystemManage.DeptAssignment[] = model.value.deptIds.map(id => ({
      dept_id: id,
      is_primary: id === model.value.primaryDeptId,
      position_id: model.value.deptPositions[id] ?? null
    }));

    if (isEdit.value && props.userId) {
      const { error } = await fetchUpdateUser(props.userId, {
        name: model.value.name,
        role_codes: model.value.roleCodes,
        dept_assignments: deptAssignments
      });
      if (error) return;
      window.$message?.success('用户已更新');
    } else {
      const { error } = await fetchCreateUser({
        username: model.value.username.trim(),
        name: model.value.name.trim(),
        role_codes: model.value.roleCodes,
        dept_assignments: deptAssignments,
        password: model.value.password || undefined
      });
      if (error) return;
      window.$message?.success(
        model.value.password ? '用户已创建' : '用户已创建（未设置初始密码，请提醒重置密码后使用）'
      );
    }
    closeDrawer();
    emit('submitted');
  } finally {
    endLoading();
  }
}
</script>

<template>
  <NDrawer v-model:show="visible" display-directive="show" :width="400">
    <NDrawerContent :title="isEdit ? '编辑用户' : '新建用户'" closable>
      <NForm
        ref="formRef"
        :model="model"
        :rules="rules"
        label-placement="top"
        label-width="auto"
        require-mark-placement="right-hanging"
      >
        <NFormItem label="登录账号" path="username">
          <NInput v-model:value="model.username" :disabled="isEdit" placeholder="登录账号，创建后不可修改" />
        </NFormItem>
        <NFormItem label="姓名" path="name">
          <NInput v-model:value="model.name" placeholder="请输入姓名" />
        </NFormItem>
        <NFormItem label="角色" path="roleCodes">
          <NSelect
            v-model:value="model.roleCodes"
            multiple
            :options="roleOptions"
            placeholder="可多选；不选则无管理角色"
          />
        </NFormItem>
        <NFormItem label="所属部门" path="deptIds">
          <div class="dept-field">
            <!-- cascade 关闭：勾选父部门不会自动勾选全部子部门（归属按勾选精确提交） -->
            <NTreeSelect
              multiple
              checkable
              :cascade="false"
              check-strategy="child"
              :value="model.deptIds"
              :options="deptOptions"
              key-field="id"
              label-field="name"
              children-field="children"
              placeholder="可多选"
              max-tag-count="responsive"
              @update:value="handleDeptIdsChange"
            />
            <template v-if="primaryOptions.length">
              <div class="dept-field__primary-label">主部门</div>
              <NRadioGroup
                :value="model.primaryDeptId"
                size="small"
                @update:value="(value: string) => (model.primaryDeptId = value)"
              >
                <NRadio v-for="opt in primaryOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </NRadio>
              </NRadioGroup>
            </template>
          </div>
        </NFormItem>
        <NFormItem v-if="!isEdit" label="初始密码" path="password">
          <NInput v-model:value="model.password" type="password" show-password-on="click" placeholder="至少 8 位" />
          <template #feedback>
            <span class="pwd-hint">留空则不设置初始密码，需管理员重置密码后方可登录</span>
          </template>
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace :size="12" justify="end">
          <NButton size="small" @click="closeDrawer">取消</NButton>
          <NButton
            type="primary"
            size="small"
            :loading="submitLoading || (isEdit && !detailLoaded)"
            :disabled="isEdit && !detailLoaded"
            @click="handleSubmit"
          >
            {{ isEdit ? '保存' : '创建' }}
          </NButton>
        </NSpace>
      </template>
    </NDrawerContent>
  </NDrawer>
</template>

<style scoped>
/* 部门选择区：树选择 + 主部门单选同卡片排布 */
.dept-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.dept-field__primary-label {
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
}

.pwd-hint {
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
}
</style>
