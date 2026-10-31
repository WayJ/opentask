<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  type DataTableColumns,
  type FormInst,
  type FormRules,
  NButton,
  NDataTable,
  NDescriptions,
  NDescriptionsItem,
  NDivider,
  NForm,
  NFormItem,
  NModal,
  NSelect,
  NSpace,
  NTag,
  useMessage
} from 'naive-ui';
import {
  type RdGroup,
  type RdGroupMember,
  addGroupMember,
  deleteRdGroup,
  getRdGroup,
  removeGroupMember
} from '@/service/api/work-management';

const router = useRouter();
const route = useRoute();
const message = useMessage();

const loading = ref(false);
const group = ref<RdGroup | null>(null);
const showAddMemberModal = ref(false);
const addingMember = ref(false);
const loadingUsers = ref(false);

const addMemberFormRef = ref<FormInst | null>(null);
const addMemberForm = ref({
  user_id: '',
  role: 'member'
});

const availableUsers = ref<any[]>([]);

const addMemberRules: FormRules = {
  user_id: {
    required: true,
    message: '请选择成员',
    trigger: 'change'
  },
  role: {
    required: true,
    message: '请选择角色',
    trigger: 'change'
  }
};

const roleOptions = [
  { label: '产品总监', value: 'director' },
  { label: '组长', value: 'leader' },
  { label: '成员', value: 'member' }
];

const availableUserOptions = computed(() => {
  const existingMemberIds = (group.value?.members || []).map(m => m.user_id);
  return availableUsers.value
    .filter(user => !existingMemberIds.includes(user.id))
    .map(user => ({
      label: user.username || user.name || user.id,
      value: user.id
    }));
});

const fetchGroup = async (id: string) => {
  loading.value = true;
  try {
    const data = await getRdGroup(id);
    group.value = data;
  } catch {
    message.error('加载失败');
  } finally {
    loading.value = false;
  }
};

const fetchUsers = async () => {
  loadingUsers.value = true;
  try {
    // 待接入：从用户服务获取用户列表
    availableUsers.value = [
      { id: '1', username: '张三' },
      { id: '2', username: '李四' },
      { id: '3', username: '王五' }
    ];
  } catch {
    message.error('加载用户列表失败');
  } finally {
    loadingUsers.value = false;
  }
};

const handleAddMember = async () => {
  if (!addMemberFormRef.value || !group.value) return;

  try {
    await addMemberFormRef.value.validate();
    addingMember.value = true;

    await addGroupMember(group.value.id, {
      user_id: addMemberForm.value.user_id,
      role: addMemberForm.value.role
    });

    message.success('添加成功');
    showAddMemberModal.value = false;
    addMemberForm.value = { user_id: '', role: 'member' };
    await fetchGroup(group.value.id);
  } catch (error: any) {
    if (error?.errorFields) {
      message.error('请检查表单填写');
    } else {
      message.error('添加失败');
    }
  } finally {
    addingMember.value = false;
  }
};

const handleRemoveMember = async (userId: string) => {
  if (!group.value) return;
  const groupId = group.value.id;

  window.$dialog?.warning({
    title: '确认移除',
    content: '确定要移除此成员吗？',
    positiveText: '移除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await removeGroupMember(groupId, userId);
        message.success('移除成功');
        await fetchGroup(groupId);
      } catch {
        message.error('移除失败');
      }
    }
  });
};

const memberColumns: DataTableColumns<RdGroupMember> = [
  { title: '成员', key: 'user_name' },
  {
    title: '角色',
    key: 'role',
    render: (row: RdGroupMember) => {
      const roleMap: Record<string, { label: string; type: 'success' | 'info' | 'default' }> = {
        director: { label: '产品总监', type: 'success' },
        leader: { label: '组长', type: 'info' },
        member: { label: '成员', type: 'default' }
      };
      const role = roleMap[row.role] || { label: row.role, type: 'default' };
      return h(NTag, { type: role.type }, () => role.label);
    }
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: RdGroupMember) =>
      h(
        NButton,
        {
          size: 'small',
          type: 'error',
          onClick: () => handleRemoveMember(row.user_id)
        },
        () => '移除'
      )
  }
];

const handleEdit = () => {
  // 待实现：跳转到编辑页面
  message.info('编辑功能待实现');
};

const handleDelete = () => {
  if (!group.value) return;
  const groupId = group.value.id;

  window.$dialog?.warning({
    title: '确认删除',
    content: '确定要删除此研发组吗？',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteRdGroup(groupId);
        message.success('删除成功');
        router.push('/work-management/rd-groups');
      } catch {
        message.error('删除失败');
      }
    }
  });
};

const handleBack = () => router.back();

onMounted(async () => {
  const id = route.params.id as string;
  await fetchGroup(id);
  await fetchUsers();
});
</script>

<template>
  <div class="rd-group-detail">
    <NPageHeader title="研发组详情" @back="handleBack" />
    <NCard class="mt-4" :loading="loading">
      <template v-if="group">
        <!-- 基本信息 -->
        <NDescriptions label-placement="left" :column="2" bordered>
          <NDescriptionsItem label="研发组名称" :span="2">
            {{ group.name }}
          </NDescriptionsItem>
          <NDescriptionsItem label="产品总监">
            {{ group.director_name || group.director_id }}
          </NDescriptionsItem>
          <NDescriptionsItem label="组长">
            {{ group.leader_name || group.leader_id }}
          </NDescriptionsItem>
          <NDescriptionsItem label="状态">
            <NTag :type="group.status === 'active' ? 'success' : 'default'">
              {{ group.status === 'active' ? '活跃' : '停用' }}
            </NTag>
          </NDescriptionsItem>
          <NDescriptionsItem label="成员数量">{{ group.members?.length || 0 }} 人</NDescriptionsItem>
          <NDescriptionsItem v-if="group.description" label="描述" :span="2">
            {{ group.description }}
          </NDescriptionsItem>
        </NDescriptions>

        <!-- 操作按钮 -->
        <NSpace class="mt-4">
          <NButton type="primary" @click="showAddMemberModal = true">添加成员</NButton>
          <NButton @click="handleEdit">编辑</NButton>
          <NButton type="error" @click="handleDelete">删除</NButton>
        </NSpace>

        <!-- 成员列表 -->
        <NDivider />
        <div>
          <h3 class="mb-2">成员列表 ({{ group.members?.length || 0 }})</h3>
          <NDataTable :columns="memberColumns" :data="group.members || []" :pagination="false" />
        </div>
      </template>
    </NCard>

    <!-- 添加成员弹窗 -->
    <NModal v-model:show="showAddMemberModal" preset="dialog" title="添加成员">
      <NForm
        ref="addMemberFormRef"
        :model="addMemberForm"
        :rules="addMemberRules"
        label-placement="left"
        label-width="100px"
      >
        <NFormItem label="成员" path="user_id">
          <NSelect
            v-model:value="addMemberForm.user_id"
            :options="availableUserOptions"
            :loading="loadingUsers"
            placeholder="请选择成员"
            filterable
          />
        </NFormItem>
        <NFormItem label="角色" path="role">
          <NSelect v-model:value="addMemberForm.role" :options="roleOptions" placeholder="请选择角色" />
        </NFormItem>
      </NForm>
      <template #action>
        <NButton @click="showAddMemberModal = false">取消</NButton>
        <NButton type="primary" :loading="addingMember" @click="handleAddMember">添加</NButton>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.rd-group-detail {
  padding: 16px;
}

.mt-4 {
  margin-top: 16px;
}

.mb-2 {
  margin-bottom: 8px;
}
</style>
