<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { fetchChangePassword } from '@/service/api';
import { useAuthStore } from '@/store/modules/auth';
import { useRouterPush } from '@/hooks/common/router';
import { useFormRules, useNaiveForm } from '@/hooks/common/form';
import { $t } from '@/locales';

defineOptions({
  name: 'ChangePassword'
});

const authStore = useAuthStore();
const { toggleLoginModule, redirectFromLogin } = useRouterPush();
const { formRef, validate } = useNaiveForm();

interface FormModel {
  oldPassword: string;
  newPassword: string;
  confirmPassword: string;
}

const model: FormModel = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
});

const submitting = ref(false);

/** 新密码强度：至少 8 位，且同时包含字母和数字（与后端弱密码校验一致） */
const REG_NEW_PWD = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/;

type RuleRecord = Partial<Record<keyof FormModel, App.Global.FormRule[]>>;

const rules = computed<RuleRecord>(() => {
  const { createConfirmPwdRule, createRequiredRule } = useFormRules();

  return {
    oldPassword: [createRequiredRule($t('form.pwd.required'))],
    newPassword: [
      createRequiredRule($t('form.pwd.required')),
      {
        pattern: REG_NEW_PWD,
        message: $t('page.login.changePassword.pwdRule'),
        trigger: 'input'
      }
    ],
    confirmPassword: createConfirmPwdRule(model.newPassword)
  };
});

async function handleSubmit() {
  await validate();

  submitting.value = true;
  const { data, error } = await fetchChangePassword({
    oldPassword: model.oldPassword,
    newPassword: model.newPassword
  });
  submitting.value = false;

  if (!error) {
    // 改密成功返回新的正常 token 对：写入 storage、拉取用户信息并跳转首页
    const pass = await authStore.loginByToken(data);

    if (pass) {
      window.$notification?.success({
        title: $t('page.login.changePassword.changeSuccess'),
        content: $t('page.login.common.welcomeBack', { userName: authStore.userInfo.userName }),
        duration: 4500
      });
      await redirectFromLogin();
    } else {
      window.$message?.error($t('page.login.changePassword.changeFailed'));
    }

    return;
  }

  // 旧密码错误返回 401（全局拦截器对该场景静默，这里自行提示）
  if (error.response?.status === 401) {
    window.$message?.error($t('page.login.changePassword.oldPwdError'));
    return;
  }

  const respData = error.response?.data as { message?: string; detail?: string } | undefined;
  window.$message?.error(respData?.message || respData?.detail || $t('page.login.changePassword.changeFailed'));
}
</script>

<template>
  <NForm ref="formRef" :model="model" :rules="rules" size="large" :show-label="false" @keyup.enter="handleSubmit">
    <NAlert type="info" :show-icon="true" class="mb-18px">{{ $t('page.login.changePassword.tip') }}</NAlert>
    <NFormItem path="oldPassword">
      <NInput
        v-model:value="model.oldPassword"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.changePassword.oldPasswordPlaceholder')"
      />
    </NFormItem>
    <NFormItem path="newPassword">
      <NInput
        v-model:value="model.newPassword"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.changePassword.newPasswordPlaceholder')"
      />
    </NFormItem>
    <NFormItem path="confirmPassword">
      <NInput
        v-model:value="model.confirmPassword"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.common.confirmPasswordPlaceholder')"
      />
    </NFormItem>
    <NSpace vertical :size="18" class="w-full">
      <NButton type="primary" size="large" round block :loading="submitting" @click="handleSubmit">
        {{ $t('common.confirm') }}
      </NButton>
      <NButton size="large" round block @click="toggleLoginModule('pwd-login')">
        {{ $t('page.login.common.back') }}
      </NButton>
    </NSpace>
  </NForm>
</template>

<style scoped></style>
