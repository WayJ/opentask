<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { loginModuleRecord } from '@/constants/app';
import { fetchDingtalkConfig } from '@/service/api';
import { useAuthStore } from '@/store/modules/auth';
import { useRouterPush } from '@/hooks/common/router';
import { useFormRules, useNaiveForm } from '@/hooks/common/form';
import { $t } from '@/locales';

defineOptions({
  name: 'PwdLogin'
});

const authStore = useAuthStore();
const { toggleLoginModule } = useRouterPush();
const { formRef, validate } = useNaiveForm();

interface FormModel {
  userName: string;
  password: string;
}

const model: FormModel = reactive({
  userName: '',
  password: ''
});

// ===== 钉钉登录入口（后端配置 DINGTALK_APP_KEY/SECRET 后才显示） =====
const dingtalkEnabled = ref(false);
const dingtalkAppKey = ref('');

onMounted(async () => {
  // 开发环境自动填充测试账号
  if (import.meta.env.DEV) {
    const testUsername = import.meta.env.VITE_TEST_USERNAME;
    const testPassword = import.meta.env.VITE_TEST_PASSWORD;

    if (testUsername) {
      model.userName = testUsername;
    }
    if (testPassword) {
      model.password = testPassword;
    }
  }

  const { error, data } = await fetchDingtalkConfig();
  if (!error && data?.enabled && data.appKey) {
    dingtalkEnabled.value = true;
    dingtalkAppKey.value = data.appKey;
  }
});

function handleDingtalkLogin() {
  if (!dingtalkAppKey.value) return;
  const redirectUri = encodeURIComponent(`${window.location.origin}/login/dingtalk-callback`);
  const state = Math.random().toString(36).slice(2);
  window.location.href =
    `https://login.dingtalk.com/oauth2/auth?redirect_uri=${redirectUri}` +
    `&response_type=code&client_id=${dingtalkAppKey.value}&scope=openid&state=${state}`;
}

const rules = computed<Record<keyof FormModel, App.Global.FormRule[]>>(() => {
  // inside computed to make locale reactive, if not apply i18n, you can define it without computed
  const { formRules } = useFormRules();

  return {
    userName: formRules.userName,
    password: formRules.pwd
  };
});

async function handleSubmit() {
  await validate();
  const result = await authStore.login(model.userName, model.password);

  // 受限 token（首次登录强制改密）：跳转改密模块
  if (result.mustChangePassword) {
    await toggleLoginModule('change-password');
  }
}

// const accounts = computed(() => [
//   {
//     key: 'super',
//     label: $t('page.login.pwdLogin.superAdmin'),
//     userName: 'Super',
//     password: '123456'
//   },
//   {
//     key: 'admin',
//     label: $t('page.login.pwdLogin.admin'),
//     userName: 'Admin',
//     password: '123456'
//   },
//   {
//     key: 'user',
//     label: $t('page.login.pwdLogin.user'),
//     userName: 'User',
//     password: '123456'
//   }
// ]);
</script>

<template>
  <NForm ref="formRef" :model="model" :rules="rules" size="large" :show-label="false" @keyup.enter="handleSubmit">
    <NFormItem path="userName">
      <NInput v-model:value="model.userName" :placeholder="$t('page.login.common.userNamePlaceholder')" />
    </NFormItem>
    <NFormItem path="password">
      <NInput
        v-model:value="model.password"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.common.passwordPlaceholder')"
      />
    </NFormItem>
    <NSpace vertical :size="24">
      <div class="flex-y-center justify-between">
        <NCheckbox>{{ $t('page.login.pwdLogin.rememberMe') }}</NCheckbox>
        <NButton quaternary @click="toggleLoginModule('reset-pwd')">
          {{ $t('page.login.pwdLogin.forgetPassword') }}
        </NButton>
      </div>
      <NButton type="primary" size="large" round block :loading="authStore.loginLoading" @click="handleSubmit">
        {{ $t('common.confirm') }}
      </NButton>
      <NDivider class="text-14px text-#666 !m-0">{{ $t('page.login.pwdLogin.otherAccountLogin') }}</NDivider>

      <div class="flex-y-center gap-12px">
        <NButton class="flex-1" block @click="toggleLoginModule('code-login')">
          {{ $t(loginModuleRecord['code-login']) }}
        </NButton>
        <NButton v-if="dingtalkEnabled" class="flex-1" block @click="handleDingtalkLogin">
          <template #icon>
            <svg class="dingtalk-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M12 2C6.48 2 2 5.94 2 10.8c0 2.63 1.34 4.99 3.44 6.55l-.86 2.58a.4.4 0 0 0 .56.48l2.96-1.5c1.23.34 2.53.5 3.9.49c5.52 0 10-3.94 10-8.8C22 5.94 17.52 2 12 2zm2.29 10.73l-1.1-.02l-2.4 1.86c-.1.08-.22.03-.22-.1l.06-1.72c-2.02-.28-3.38-1.36-3.38-2.94c0-1.7 1.66-2.93 4.08-2.93c2.42 0 4.08 1.23 4.08 2.93c0 1.44-1.12 2.49-2.82 2.87l-.3.05z"
              />
            </svg>
          </template>
          {{ $t('page.login.pwdLogin.dingtalkLogin') }}
        </NButton>
      </div>
      <!--
 <div class="flex-center gap-12px">
        <NButton v-for="item in accounts" :key="item.key" type="primary" @click="handleAccountLogin(item)">
          {{ item.label }}
        </NButton>
      </div> 
-->
    </NSpace>
  </NForm>
</template>

<style scoped>
.dingtalk-icon {
  width: 18px;
  height: 18px;
  color: #0089ff;
}
</style>
