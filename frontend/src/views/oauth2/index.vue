<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { fetchOAuthAuthorizeContext, fetchOAuthAuthorizeDecision } from '@/service/api/oauth2';
import { $t } from '@/locales';

/**
 * OAuth2 授权同意页（路由 /oauth2/authorize，elegant-router 路由名 oauth2）
 *
 * 流程：
 * 1. 从 URL query 读 client_id / redirect_uri / response_type / scope / state；
 * 2. 调 GET /api/oauth2/authorize/context 让后端校验（client 状态、redirect_uri
 *    白名单精确匹配、scope 允许集）并取回应用名/描述/scope 清单；
 * 3. 用户点「同意授权」/「拒绝」→ POST /api/oauth2/authorize/approve
 *    （后端**重新校验**全部参数）→ 返回应跳转的完整 URL → 整页跳转。
 *
 * 未登录时由路由守卫拦到登录页，登录后带 ?redirect= 回本页（守卫既有机制）。
 */

defineOptions({
  name: 'OAuth2'
});

const route = useRoute();

const status = ref<'loading' | 'ready' | 'submitting' | 'error'>('loading');
const errorMsg = ref('');
const context = ref<{
  client_id: string;
  client_name: string;
  client_description?: string | null;
  scope: string[];
  redirect_uri: string;
  redirect_host: string;
  state?: string | null;
  code_challenge?: string | null;
  code_challenge_method?: string | null;
  resource?: string | null;
} | null>(null);

/** scope → 中文说明（未知 scope 回退展示原值，不静默吞掉） */
const scopeLabels: Record<string, string> = {
  'read:tasks': '读取你的任务列表与详情',
  'read:projects': '读取你的项目列表与详情',
  'read:requirements': '读取你的需求列表与详情',
  profile: '读取你的基本资料（用户名、姓名）'
};

function scopeText(scope: string) {
  return scopeLabels[scope] || scope;
}

const scopeList = computed(() => (context.value?.scope || []).map(scope => ({ key: scope, text: scopeText(scope) })));

function queryString(key: string): string {
  const value = route.query[key];
  return typeof value === 'string' ? value : '';
}

function getErrMsg(err: unknown, fallback: string) {
  const e = err as { response?: { data?: { detail?: string; message?: string } }; message?: string } | null;
  return e?.response?.data?.detail || e?.response?.data?.message || e?.message || fallback;
}

async function loadContext() {
  const clientId = queryString('client_id');
  const redirectUri = queryString('redirect_uri');
  if (!clientId || !redirectUri) {
    status.value = 'error';
    errorMsg.value = $t('page.oauth2.consent.missingParams');
    return;
  }

  const { error, data } = await fetchOAuthAuthorizeContext({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: queryString('response_type') || 'code',
    scope: queryString('scope'),
    state: queryString('state') || undefined,
    code_challenge: queryString('code_challenge') || undefined,
    code_challenge_method: queryString('code_challenge_method') || undefined,
    resource: queryString('resource') || undefined
  });
  if (error) {
    status.value = 'error';
    errorMsg.value = getErrMsg(error, $t('page.oauth2.consent.invalidRequest'));
    return;
  }
  context.value = data;
  status.value = 'ready';
}

async function decide(decision: 'approve' | 'deny') {
  if (!context.value) return;
  status.value = 'submitting';
  const { error, data } = await fetchOAuthAuthorizeDecision({
    client_id: context.value.client_id,
    redirect_uri: context.value.redirect_uri,
    scope: (context.value.scope || []).join(' '),
    state: context.value.state || undefined,
    code_challenge: context.value.code_challenge || undefined,
    code_challenge_method: context.value.code_challenge_method || undefined,
    resource: context.value.resource || undefined,
    decision
  });
  if (error) {
    status.value = 'error';
    errorMsg.value = getErrMsg(error, $t('page.oauth2.consent.decideFailed'));
    return;
  }
  // 整页跳转到客户端回调地址（带 code 或 error 与 state）
  window.location.replace(data.redirect_to);
}

onMounted(() => {
  loadContext();
});
</script>

<template>
  <div class="oauth2-consent">
    <NCard v-if="status === 'loading'" class="oauth2-consent__card" :bordered="false">
      <div class="oauth2-consent__loading">
        <NSpin size="medium" />
        <p class="oauth2-consent__hint">{{ $t('page.oauth2.consent.loading') }}</p>
      </div>
    </NCard>

    <NCard v-else-if="status === 'error'" class="oauth2-consent__card" :bordered="false">
      <NAlert type="error" :show-icon="true" class="oauth2-consent__alert">
        {{ errorMsg || $t('page.oauth2.consent.invalidRequest') }}
      </NAlert>
    </NCard>

    <NCard v-else-if="context" class="oauth2-consent__card" :bordered="false">
      <h1 class="oauth2-consent__title">{{ $t('page.oauth2.consent.title') }}</h1>
      <p class="oauth2-consent__lead">
        {{ $t('page.oauth2.consent.lead', { appName: context.client_name }) }}
      </p>

      <div class="oauth2-consent__block">
        <h2 class="oauth2-consent__subtitle">{{ $t('page.oauth2.consent.scopeTitle') }}</h2>
        <ul class="oauth2-consent__scope-list">
          <li v-for="item in scopeList" :key="item.key" class="oauth2-consent__scope-item">
            <NCheckbox :checked="true" size="small" disabled />
            <span>{{ item.text }}</span>
          </li>
        </ul>
      </div>

      <div class="oauth2-consent__block">
        <h2 class="oauth2-consent__subtitle">{{ $t('page.oauth2.consent.redirectTitle') }}</h2>
        <p class="oauth2-consent__redirect">
          {{ context.redirect_host }}
        </p>
      </div>

      <p v-if="context.client_description" class="oauth2-consent__desc">
        {{ context.client_description }}
      </p>

      <div class="oauth2-consent__actions">
        <NButton size="large" :loading="status === 'submitting'" @click="decide('deny')">
          {{ $t('page.oauth2.consent.deny') }}
        </NButton>
        <NButton size="large" type="primary" :loading="status === 'submitting'" @click="decide('approve')">
          {{ $t('page.oauth2.consent.approve') }}
        </NButton>
      </div>
    </NCard>
  </div>
</template>

<style scoped>
.oauth2-consent {
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  background: var(--bg-color, #f7f8fa);
}

.oauth2-consent__card {
  width: 100%;
  max-width: 520px;
  border-radius: 12px;
  box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
}

.oauth2-consent__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 24px 0;
}

.oauth2-consent__hint {
  margin: 0;
  font-size: 14px;
  color: var(--vk-muted, #6a6e64);
}

.oauth2-consent__alert {
  width: 100%;
}

.oauth2-consent__title {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
  color: var(--vk-text, #111827);
}

.oauth2-consent__lead {
  margin: 0 0 20px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--vk-muted, #6a6e64);
}

.oauth2-consent__block {
  margin-bottom: 18px;
}

.oauth2-consent__subtitle {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--vk-text, #111827);
}

.oauth2-consent__scope-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.oauth2-consent__scope-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 14px;
  color: var(--vk-text, #111827);
}

.oauth2-consent__redirect {
  margin: 0;
  font-size: 13px;
  word-break: break-all;
  color: var(--vk-muted, #6a6e64);
}

.oauth2-consent__desc {
  margin: 0 0 18px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--vk-muted, #6a6e64);
}

.oauth2-consent__actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
