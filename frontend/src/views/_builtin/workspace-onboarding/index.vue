<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { fetchEnsureOwnerWorkspace } from '@/service/api';
import { useAuthStore } from '@/store/modules/auth';
import { $t } from '@/locales';

defineOptions({ name: 'WorkspaceOnboarding' });

const router = useRouter();
const authStore = useAuthStore();
const name = ref('OpenTask');
const submitting = ref(false);
const errorText = ref('');

async function createWorkspace() {
  if (authStore.workspaceGate !== 'onboarding') return;
  const workspaceName = name.value.trim() || 'OpenTask';
  submitting.value = true;
  errorText.value = '';
  const { data, error } = await fetchEnsureOwnerWorkspace({ name: workspaceName });
  submitting.value = false;
  if (error || !data?.id) {
    errorText.value = '创建工作区失败，请重试';
    return;
  }
  authStore.markWorkspaceReady(data.id);
  await router.replace({ name: 'issue_list' });
}

async function retry() {
  errorText.value = '';
  await authStore.ensureWorkspaceResolved(true);
  if (authStore.workspaceGate === 'ready') {
    await router.replace({ name: 'root' });
  }
}

async function logout() {
  await authStore.resetStore();
}
</script>

<template>
  <div class="ot-public-page min-h-screen">
    <div class="ot-public-card max-w-420px p-32px">
      <div class="mb-24px flex-y-center gap-12px">
        <SystemLogo class="text-40px" />
        <h1 class="text-20px font-600">{{ $t('system.title') }}</h1>
      </div>
      <p class="ot-muted mb-16px text-14px">当前账号还没有可用工作区。创建一个之后再进入问题列表。</p>
      <template v-if="authStore.workspaceGate === 'error'">
        <p class="ot-error mb-16px text-14px">暂时读不到工作区列表，没有创建新的工作区。</p>
        <NButton type="primary" @click="retry">重试</NButton>
      </template>
      <template v-else>
        <NInput v-model:value="name" placeholder="OpenTask" class="mb-16px" />
        <p v-if="errorText" class="ot-error mb-12px text-14px">{{ errorText }}</p>
        <NButton type="primary" :loading="submitting" :disabled="submitting" @click="createWorkspace">
          创建工作区
        </NButton>
      </template>
      <NButton class="mt-16px" quaternary block @click="logout">退出登录</NButton>
    </div>
  </div>
</template>
