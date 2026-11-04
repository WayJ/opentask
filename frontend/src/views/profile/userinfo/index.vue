<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import type { FormRules } from 'naive-ui';
import { NButton, NCard, NDescriptions, NDescriptionsItem, NSpace, NSpin, NTag } from 'naive-ui';
import { useLoading } from '@sa/hooks';
import { getRoleLabel, getRoleType } from '@/constants/role';
import { fetchChangePassword, fetchGetCurrentUser } from '@/service/api';
import { useAuthStore } from '@/store/modules/auth';
import { useRouterPush } from '@/hooks/common/router';
import { useFormRules, useNaiveForm } from '@/hooks/common/form';
import { $t } from '@/locales';

defineOptions({
  name: 'UserProfile'
});

const { routerPushByKey } = useRouterPush();
const { loading, startLoading, endLoading } = useLoading();
const authStore = useAuthStore();

// 用户信息
const userInfo = ref<Api.SystemManage.CurrentUser | null>(null);

// 加载用户信息
async function loadUserInfo() {
  startLoading();
  const { error, data } = await fetchGetCurrentUser();
  if (!error && data) {
    userInfo.value = data;
  } else {
    window.$message?.error('加载用户信息失败');
  }
  endLoading();
}

// 打开主题设置
function openThemeSettings() {
  routerPushByKey('setting_theme');
}

// 角色标签类型
const getRoleTagType = (role: Api.SystemManage.UserRoleType) => {
  return getRoleType(role);
};

// ===== 修改密码 =====
const { formRef: pwdFormRef, validate: validatePwdForm } = useNaiveForm();
const pwdSubmitting = ref(false);

interface PwdFormModel {
  oldPassword: string;
  newPassword: string;
  confirmPassword: string;
}

const pwdModel = reactive<PwdFormModel>({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
});

/** 新密码强度：至少 8 位，且同时包含字母和数字（与后端弱密码校验一致） */
const REG_NEW_PWD = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/;

const pwdRules = computed<FormRules>(() => {
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
    confirmPassword: createConfirmPwdRule(pwdModel.newPassword)
  };
});

async function handleChangePassword() {
  await validatePwdForm();
  pwdSubmitting.value = true;
  const { error } = await fetchChangePassword({
    oldPassword: pwdModel.oldPassword,
    newPassword: pwdModel.newPassword
  });
  pwdSubmitting.value = false;

  if (error) {
    // 旧密码错误返回 401（全局拦截器对该场景静默，这里自行提示）
    if ((error as { response?: { status?: number } }).response?.status === 401) {
      window.$message?.error($t('page.login.changePassword.oldPwdError'));
      return;
    }
    const respData = (error as { response?: { data?: { message?: string; detail?: string } } }).response?.data;
    window.$message?.error(respData?.message || respData?.detail || $t('page.login.changePassword.changeFailed'));
    return;
  }

  // 改密后旧 token 失效：清理本地会话并回到登录页重新登录
  window.$dialog?.info({
    title: $t('page.login.changePassword.changeSuccess'),
    content: $t('profile.pwd.reLoginTip'),
    positiveText: $t('page.login.common.confirm'),
    onPositiveClick: async () => {
      await authStore.resetStore();
      window.location.href = '/login';
    }
  });
}

// ===== 钉钉绑定状态 =====
const dingtalkBound = computed(() => Boolean(userInfo.value?.dingtalkUserId));

onMounted(() => {
  loadUserInfo();
});
</script>

<template>
  <div class="profile-container">
    <NSpin :show="loading">
      <div class="profile-content">
        <!-- 页面标题 -->
        <div class="profile-header">
          <h2 class="profile-title">{{ $t('route.profile') }}</h2>
          <p class="profile-subtitle">{{ $t('profile.subtitle') }}</p>
        </div>

        <!-- 用户信息卡片 -->
        <NCard :title="$t('profile.basicInfo')" class="profile-card">
          <template #header-extra>
            <NSpace>
              <NButton type="primary" @click="openThemeSettings">
                <template #icon>
                  <svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path
                      fill="currentColor"
                      d="M12 3a9 9 0 0 0 0 18c4.97 0 9-4.03 9-9s-4.03-9-9-9zm0 16a7 7 0 1 1 0-14a7 7 0 0 1 0 14zm0-13a6 6 0 1 0 0 12a6 6 0 0 0 0-12zm1 3h-2v4.414l2.293 2.293l1.414-1.414L13 12.586V9z"
                    />
                  </svg>
                </template>
                {{ $t('profile.themeSettings') }}
              </NButton>
            </NSpace>
          </template>

          <NDescriptions label-placement="left" :column="2" bordered>
            <NDescriptionsItem :label="$t('profile.account')">
              {{ userInfo?.ssoAccount || userInfo?.ssoName || '-' }}
            </NDescriptionsItem>
            <NDescriptionsItem :label="$t('profile.name')">
              {{ userInfo?.ssoName || '-' }}
            </NDescriptionsItem>
            <NDescriptionsItem :label="$t('profile.role')">
              <NSpace v-if="userInfo?.workspaceRole || userInfo?.role" :size="8">
                <NTag
                  v-if="userInfo?.workspaceRole"
                  :type="getRoleTagType(userInfo.workspaceRole)"
                >
                  工作区 · {{ getRoleLabel(userInfo.workspaceRole) }}
                </NTag>
                <NTag v-if="userInfo?.role" :type="getRoleTagType(userInfo.role)" :bordered="false">
                  平台 · {{ getRoleLabel(userInfo.role) }}
                </NTag>
              </NSpace>
              <span v-else>-</span>
            </NDescriptionsItem>
            <NDescriptionsItem :label="$t('profile.status')">
              <NTag :type="userInfo?.status === 1 ? 'success' : 'default'">
                {{ userInfo?.status === 1 ? $t('profile.enabled') : $t('profile.disabled') }}
              </NTag>
            </NDescriptionsItem>
            <NDescriptionsItem :label="$t('profile.organize')">
              {{ userInfo?.organizeName || '-' }}
            </NDescriptionsItem>
            <NDescriptionsItem :label="$t('profile.position')">
              {{ userInfo?.positionName || '-' }}
            </NDescriptionsItem>
            <NDescriptionsItem :label="$t('profile.userId')" :span="2">
              {{ userInfo?.id || '-' }}
            </NDescriptionsItem>
          </NDescriptions>
        </NCard>

        <!-- 修改密码卡片 -->
        <NCard :title="$t('profile.pwd.title')" class="profile-card">
          <div class="pwd-form">
            <NForm ref="pwdFormRef" :model="pwdModel" :rules="pwdRules" label-placement="top" class="pwd-form__inner">
              <NFormItem :label="$t('page.login.changePassword.oldPasswordPlaceholder')" path="oldPassword">
                <NInput
                  v-model:value="pwdModel.oldPassword"
                  type="password"
                  show-password-on="click"
                  :placeholder="$t('page.login.changePassword.oldPasswordPlaceholder')"
                />
              </NFormItem>
              <NFormItem :label="$t('page.login.changePassword.newPasswordPlaceholder')" path="newPassword">
                <NInput
                  v-model:value="pwdModel.newPassword"
                  type="password"
                  show-password-on="click"
                  :placeholder="$t('page.login.changePassword.newPasswordPlaceholder')"
                />
              </NFormItem>
              <NFormItem :label="$t('page.login.common.confirmPasswordPlaceholder')" path="confirmPassword">
                <NInput
                  v-model:value="pwdModel.confirmPassword"
                  type="password"
                  show-password-on="click"
                  :placeholder="$t('page.login.common.confirmPasswordPlaceholder')"
                  @keydown.enter="handleChangePassword"
                />
              </NFormItem>
              <NButton type="primary" :loading="pwdSubmitting" @click="handleChangePassword">
                {{ $t('profile.pwd.submit') }}
              </NButton>
            </NForm>
            <p class="pwd-form__hint">{{ $t('profile.pwd.hint') }}</p>
          </div>
        </NCard>

        <!-- 钉钉绑定卡片 -->
        <NCard :title="$t('page.profile.dingtalk.title')" class="profile-card">
          <div class="dingtalk-card">
            <div class="dingtalk-card__status">
              <NTag :type="dingtalkBound ? 'success' : 'default'">
                {{ dingtalkBound ? $t('page.profile.dingtalk.bound') : $t('page.profile.dingtalk.unbound') }}
              </NTag>
              <span v-if="dingtalkBound" class="dingtalk-card__id">
                {{ userInfo?.dingtalkUserId }}
              </span>
            </div>
            <p class="dingtalk-card__hint">{{ $t('page.profile.dingtalk.hint') }}</p>
          </div>
        </NCard>

        <!-- 权限信息卡片 -->
        <NCard :title="$t('profile.permissions')" class="profile-card">
          <NSpace vertical>
            <div class="permissions-info">
              <p class="permissions-count">
                {{ $t('profile.totalPermissions') }}: {{ userInfo?.permissions?.length || 0 }}
              </p>
            </div>
            <div v-if="userInfo && userInfo.permissions?.length > 0" class="permissions-list">
              <NTag
                v-for="permission in userInfo.permissions.slice(0, 20)"
                :key="permission"
                type="info"
                size="small"
                class="perm-tag"
              >
                {{ permission }}
              </NTag>
              <NTag
                v-if="userInfo.permissions && userInfo.permissions.length > 20"
                type="default"
                size="small"
                class="perm-tag"
              >
                +{{ userInfo.permissions.length - 20 }} more
              </NTag>
            </div>
            <div v-else class="no-permissions">
              <p>{{ $t('profile.noPermissions') }}</p>
            </div>
          </NSpace>
        </NCard>

        <!-- 快捷导航卡片 -->
        <NCard title="安全与认证" class="profile-card">
          <NSpace>
            <NButton @click="routerPushByKey('profile_ssh-keys')">SSH 密钥管理</NButton>
            <NButton @click="routerPushByKey('profile_access-tokens')">Access Token 管理</NButton>
          </NSpace>
        </NCard>
      </div>
    </NSpin>
  </div>
</template>

<style scoped lang="scss">
.profile-container {
  padding: 24px;
  min-height: calc(100vh - 120px);
  background-color: var(--bg-color);
}

.profile-content {
  max-width: 1200px;
  margin: 0 auto;
}

.profile-header {
  margin-bottom: 24px;
  text-align: center;
}

.profile-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-color-1);
  margin: 0 0 8px 0;
}

.profile-subtitle {
  font-size: 14px;
  color: var(--text-color-3);
  margin: 0;
}

.profile-card {
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }
}

.icon {
  width: 18px;
  height: 18px;
}

// 修改密码：窄表单
.pwd-form {
  display: flex;
  gap: 24px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.pwd-form__inner {
  width: 320px;
  max-width: 100%;
}

.pwd-form__hint {
  flex: 1;
  min-width: 200px;
  margin: 0;
  font-size: 12px;
  color: var(--text-color-3);
  line-height: 1.7;
}

// 钉钉绑定
.dingtalk-card__status {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.dingtalk-card__id {
  font-size: 12px;
  color: var(--text-color-2);
  font-variant-numeric: tabular-nums;
}

.dingtalk-card__hint {
  margin: 0;
  font-size: 12px;
  color: var(--text-color-3);
}

.permissions-info {
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.permissions-count {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color-1);
  margin: 0;
}

.permissions-list {
  padding: 16px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;

  :deep(.perm-tag) {
    margin: 4px;
  }
}

.no-permissions {
  padding: 24px;
  text-align: center;
  color: var(--text-color-3);
}
</style>
