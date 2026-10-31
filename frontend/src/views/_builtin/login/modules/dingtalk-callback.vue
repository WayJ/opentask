<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { fetchDingtalkCallback } from '@/service/api';
import { useAuthStore } from '@/store/modules/auth';
import { useRouterPush } from '@/hooks/common/router';
import { $t } from '@/locales';

/**
 * 钉钉登录回调页（路由 /login/dingtalk-callback）
 *
 * 钉钉授权后重定向回本页（带 authCode）→ POST /api/auth/dingtalk/callback
 * → 成功 loginByToken 进首页；失败展示原因并返回密码登录。
 */

defineOptions({
  name: 'DingtalkCallback'
});

const authStore = useAuthStore();
const router = useRouter();
const { routerPushByKey, toggleLoginModule } = useRouterPush();

const status = ref<'processing' | 'success' | 'error'>('processing');
const errorMsg = ref('');

function getErrMsg(err: unknown, fallback: string) {
  const e = err as { response?: { data?: { detail?: string; message?: string } }; message?: string } | null;
  return e?.response?.data?.detail || e?.response?.data?.message || e?.message || fallback;
}

async function handleCallback() {
  const authCode = router.currentRoute.value.query.authCode;
  if (!authCode || typeof authCode !== 'string') {
    status.value = 'error';
    errorMsg.value = $t('page.login.dingtalkCallback.noCode');
    return;
  }

  const { error, data } = await fetchDingtalkCallback(authCode);
  if (error) {
    status.value = 'error';
    errorMsg.value = getErrMsg(error, $t('page.login.dingtalkCallback.fail'));
    return;
  }

  const pass = await authStore.loginByToken(data);
  if (pass) {
    status.value = 'success';
    window.$notification?.success({
      title: $t('page.login.common.loginSuccess'),
      content: $t('page.login.common.welcomeBack', { userName: authStore.userInfo.userName }),
      duration: 4500
    });
    routerPushByKey('root');
  } else {
    status.value = 'error';
    errorMsg.value = $t('page.login.dingtalkCallback.fail');
  }
}

function backToLogin() {
  toggleLoginModule('pwd-login');
}

onMounted(() => {
  handleCallback();
});
</script>

<template>
  <div class="dingtalk-callback">
    <NSpin v-if="status === 'processing'" size="medium" />
    <p v-if="status === 'processing'" class="dingtalk-callback__text">
      {{ $t('page.login.dingtalkCallback.processing') }}
    </p>

    <template v-else-if="status === 'success'">
      <p class="dingtalk-callback__text">{{ $t('page.login.dingtalkCallback.success') }}</p>
    </template>

    <template v-else>
      <NAlert type="error" :show-icon="true" class="dingtalk-callback__error">
        {{ errorMsg || $t('page.login.dingtalkCallback.fail') }}
      </NAlert>
      <NButton size="large" round block @click="backToLogin">
        {{ $t('page.login.common.back') }}
      </NButton>
    </template>
  </div>
</template>

<style scoped>
.dingtalk-callback {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  min-height: 160px;
  justify-content: center;
}

.dingtalk-callback__text {
  margin: 0;
  font-size: 14px;
  color: var(--vk-muted, #6a6e64);
}

.dingtalk-callback__error {
  width: 100%;
  border-radius: 8px;
}
</style>
