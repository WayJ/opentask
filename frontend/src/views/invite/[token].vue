<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { NButton, NCard, NSpace, NSpin, NTag } from 'naive-ui';
import {
  type WorkspaceInviteItem,
  fetchAcceptInvite,
  fetchPreviewInvite
} from '@/service/api/workspace';
import { localStg } from '@/utils/storage';

defineOptions({ name: 'InviteLandingPage' });

const route = useRoute();
const router = useRouter();
const token = computed(() => String(route.params.token || ''));
const loading = ref(true);
const accepting = ref(false);
const preview = ref<WorkspaceInviteItem | null>(null);
const errorMsg = ref('');

const isLogin = computed(() => Boolean(localStg.get('token')));

async function loadPreview() {
  loading.value = true;
  errorMsg.value = '';
  try {
    if (!token.value) {
      errorMsg.value = '无效邀请';
      return;
    }
    const { data, error } = await fetchPreviewInvite(token.value);
    if (error || !data) {
      errorMsg.value = error?.message || '邀请不存在或已失效';
      preview.value = null;
      return;
    }
    preview.value = data;
  } finally {
    loading.value = false;
  }
}

async function accept() {
  accepting.value = true;
  try {
    const { data, error } = await fetchAcceptInvite(token.value);
    if (error) {
      window.$message?.error?.(error.message || '接受失败');
      return;
    }
    if (data?.workspaceId) {
      localStg.set('workspaceId', data.workspaceId);
    }
    window.$message?.success?.(data?.alreadyMember ? '你已是成员' : '已加入工作区');
    router.replace('/workspace/members');
  } finally {
    accepting.value = false;
  }
}

function goLogin() {
  router.push({
    name: 'login',
    params: { module: 'pwd-login' },
    query: { redirect: `/invite/${token.value}` }
  });
}

function goRegister() {
  router.push({
    name: 'login',
    params: { module: 'register' },
    query: { invite: token.value, redirect: `/invite/${token.value}` }
  });
}

onMounted(loadPreview);
</script>

<template>
  <div class="min-h-screen flex-center p-24px">
    <NCard title="工作区邀请" style="width: 420px" :bordered="false" class="card-wrapper">
      <NSpin :show="loading">
        <NSpace v-if="errorMsg" vertical>
          <div class="text-error">{{ errorMsg }}</div>
          <NButton @click="goLogin">去登录</NButton>
        </NSpace>
        <NSpace v-else-if="preview" vertical :size="16">
          <div>
            工作区：<strong>{{ preview.workspaceName || preview.workspaceId }}</strong>
          </div>
          <div>
            角色：
            <NTag size="small">{{ preview.role }}</NTag>
          </div>
          <div class="text-13px text-gray-500">状态：{{ preview.status }}</div>
          <div class="text-13px text-gray-500">过期：{{ preview.expiresAt }}</div>

          <template v-if="preview.status === 'pending'">
            <NButton v-if="isLogin" type="primary" block :loading="accepting" @click="accept">
              接受邀请
            </NButton>
            <NSpace v-else vertical>
              <NButton type="primary" block @click="goRegister">注册并加入</NButton>
              <NButton block @click="goLogin">已有账号？登录后接受</NButton>
            </NSpace>
          </template>
          <div v-else class="text-warning">该邀请不可接受（{{ preview.status }}）</div>
        </NSpace>
      </NSpin>
    </NCard>
  </div>
</template>
