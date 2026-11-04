<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import {
  type DataTableColumns,
  NButton,
  NCard,
  NDataTable,
  NInput,
  NSelect,
  NSpace,
  NTag
} from 'naive-ui';
import { useAuthStore } from '@/store/modules/auth';
import { localStg } from '@/utils/storage';
import {
  type WorkspaceInviteItem,
  type WorkspaceMemberItem,
  fetchCreateWorkspaceInvite,
  fetchLeaveWorkspace,
  fetchRemoveWorkspaceMember,
  fetchRevokeWorkspaceInvite,
  fetchUpdateWorkspaceMemberRole,
  fetchWorkspace,
  fetchWorkspaceInvites,
  fetchWorkspaceList,
  fetchWorkspaceMembers
} from '@/service/api/workspace';

defineOptions({ name: 'WorkspaceMembersPage' });

const authStore = useAuthStore();
const loading = ref(false);
const inviting = ref(false);
const members = ref<WorkspaceMemberItem[]>([]);
const invites = ref<WorkspaceInviteItem[]>([]);
const myRole = ref<string | null>(null);
const workspaceId = ref<string>('');
const lastCreatedLink = ref('');

const inviteForm = reactive({
  email: '',
  role: 'member' as 'member' | 'viewer',
  expiresInDays: 14
});

const isOwner = computed(() => myRole.value === 'owner');
const myUserId = computed(() => String(authStore.userInfo?.userId || ''));

const roleOptions = [
  { label: 'owner', value: 'owner' },
  { label: 'member', value: 'member' },
  { label: 'viewer', value: 'viewer' }
];

const inviteRoleOptions = [
  { label: 'member', value: 'member' },
  { label: 'viewer', value: 'viewer' }
];

async function resolveWorkspaceId(): Promise<string> {
  const cached = localStg.get('workspaceId');
  if (cached) return String(cached);
  const { data, error } = await fetchWorkspaceList();
  if (error || !data?.length) throw new Error('无可用工作区');
  localStg.set('workspaceId', data[0].id);
  return data[0].id;
}

async function load() {
  loading.value = true;
  try {
    const wsId = await resolveWorkspaceId();
    workspaceId.value = wsId;
    const [wsRes, memRes] = await Promise.all([
      fetchWorkspace(wsId),
      fetchWorkspaceMembers(wsId)
    ]);
    if (wsRes.error) {
      window.$message?.error?.(wsRes.error.message || '加载工作区失败');
      return;
    }
    myRole.value = wsRes.data?.role || null;
    members.value = memRes.data || [];
    if (isOwner.value) {
      const invRes = await fetchWorkspaceInvites(wsId);
      invites.value = invRes.data || [];
    } else {
      invites.value = [];
    }
  } finally {
    loading.value = false;
  }
}

async function changeRole(row: WorkspaceMemberItem, role: string) {
  if (!workspaceId.value) return;
  const { error } = await fetchUpdateWorkspaceMemberRole(workspaceId.value, row.userId, role);
  if (error) {
    window.$message?.error?.(error.message || '更新角色失败');
    return;
  }
  window.$message?.success?.('角色已更新');
  await load();
}

async function removeMember(row: WorkspaceMemberItem) {
  if (!workspaceId.value) return;
  const { error } = await fetchRemoveWorkspaceMember(workspaceId.value, row.userId);
  if (error) {
    window.$message?.error?.(error.message || '移除失败');
    return;
  }
  window.$message?.success?.('已移除');
  await load();
}

async function leave() {
  if (!workspaceId.value) return;
  const { error } = await fetchLeaveWorkspace(workspaceId.value);
  if (error) {
    window.$message?.error?.(error.message || '离开失败');
    return;
  }
  window.$message?.success?.('已离开工作区');
  localStg.remove('workspaceId');
  window.location.href = '/';
}

async function createInvite() {
  if (!workspaceId.value) return;
  inviting.value = true;
  try {
    const { data, error } = await fetchCreateWorkspaceInvite(workspaceId.value, {
      email: inviteForm.email.trim() || undefined,
      role: inviteForm.role,
      expiresInDays: inviteForm.expiresInDays
    });
    if (error || !data?.token) {
      window.$message?.error?.(error?.message || '创建邀请失败');
      return;
    }
    const link = `${window.location.origin}/invite/${data.token}`;
    lastCreatedLink.value = link;
    try {
      await navigator.clipboard.writeText(link);
      window.$message?.success?.('邀请已创建，链接已复制');
    } catch {
      window.$message?.success?.('邀请已创建');
    }
    inviteForm.email = '';
    await load();
  } finally {
    inviting.value = false;
  }
}

async function revokeInvite(row: WorkspaceInviteItem) {
  if (!workspaceId.value) return;
  const { error } = await fetchRevokeWorkspaceInvite(workspaceId.value, row.id);
  if (error) {
    window.$message?.error?.(error.message || '撤销失败');
    return;
  }
  window.$message?.success?.('已撤销');
  await load();
}

function copyLink(tokenOrLink: string) {
  const link = tokenOrLink.startsWith('http')
    ? tokenOrLink
    : `${window.location.origin}/invite/${tokenOrLink}`;
  navigator.clipboard
    ?.writeText(link)
    .then(() => window.$message?.success?.('已复制链接'))
    .catch(() => {
      lastCreatedLink.value = link;
      window.$message?.info?.('请手动复制下方链接');
    });
}

const memberColumns: DataTableColumns<WorkspaceMemberItem> = [
  { title: '用户 ID', key: 'userId', ellipsis: { tooltip: true } },
  {
    title: '角色',
    key: 'role',
    width: 160,
    render: row =>
      isOwner.value
        ? h(NSelect, {
            value: row.role,
            options: roleOptions,
            size: 'small',
            style: { width: '120px' },
            onUpdateValue: (v: string) => changeRole(row, v)
          })
        : h(NTag, { size: 'small' }, { default: () => row.role })
  },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: row => {
      const nodes = [];
      if (isOwner.value && row.userId !== myUserId.value) {
        nodes.push(
          h(
            NButton,
            {
              size: 'tiny',
              tertiary: true,
              type: 'error',
              onClick: () => removeMember(row)
            },
            { default: () => '移除' }
          )
        );
      }
      if (row.userId === myUserId.value && row.role !== 'owner') {
        nodes.push(
          h(
            NButton,
            { size: 'tiny', tertiary: true, onClick: () => leave() },
            { default: () => '离开' }
          )
        );
      }
      return h(NSpace, null, { default: () => nodes });
    }
  }
];

const inviteColumns: DataTableColumns<WorkspaceInviteItem> = [
  { title: '邮箱备注', key: 'email', render: row => row.email || '—' },
  { title: '角色', key: 'role', width: 100 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: row => h(NTag, { size: 'small' }, { default: () => row.status })
  },
  { title: '过期', key: 'expiresAt', width: 180 },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: row =>
      h(NSpace, null, {
        default: () => [
          row.status === 'pending'
            ? h(
                NButton,
                {
                  size: 'tiny',
                  tertiary: true,
                  type: 'error',
                  onClick: () => revokeInvite(row)
                },
                { default: () => '撤销' }
              )
            : null
        ]
      })
  }
];

onMounted(load);
</script>

<template>
  <div class="h-full flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
    <NCard title="成员 Members" :bordered="false" class="card-wrapper">
      <NSpace vertical :size="12">
        <NSpace v-if="myRole && myRole !== 'owner'">
          <NButton @click="leave">离开工作区</NButton>
        </NSpace>
        <NDataTable
          :columns="memberColumns"
          :data="members"
          :loading="loading"
          :bordered="false"
          size="small"
        />
      </NSpace>
    </NCard>

    <NCard v-if="isOwner" title="邀请 Invites" :bordered="false" class="card-wrapper sm:flex-1-hidden">
      <NSpace vertical :size="16">
        <NSpace>
          <NInput v-model:value="inviteForm.email" placeholder="可选邮箱备注" style="width: 200px" />
          <NSelect
            v-model:value="inviteForm.role"
            :options="inviteRoleOptions"
            style="width: 120px"
          />
          <NButton type="primary" :loading="inviting" @click="createInvite">创建邀请链接</NButton>
        </NSpace>
        <div v-if="lastCreatedLink" class="text-13px text-gray-500 break-all">
          最近链接：
          <a class="text-primary cursor-pointer" @click="copyLink(lastCreatedLink)">{{ lastCreatedLink }}</a>
        </div>
        <NDataTable
          :columns="inviteColumns"
          :data="invites"
          :loading="loading"
          :bordered="false"
          size="small"
        />
      </NSpace>
    </NCard>
  </div>
</template>
