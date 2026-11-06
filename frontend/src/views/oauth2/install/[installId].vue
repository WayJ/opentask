<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { NAlert, NButton, NCode, NDescriptions, NDescriptionsItem, NSpace, NSpin, NTag, NText } from 'naive-ui';
import { useLoading } from '@sa/hooks';
import {
  fetchApproveOAuthInstallRequest,
  fetchGetOAuthInstallRequest,
  fetchRejectOAuthInstallRequest
} from '@/service/api';
import { scopeEndpoint, scopeLabel } from '@/utils/oauth2-client';
import type { Api } from '@/typings/api';

/**
 * OAuth 安装确认页（管理员，路由 /oauth2/install/:installId）
 *
 * 契约（docs/superpowers/contracts/2026-11-06-e101-oauth2-install-contract.md §3.C）：
 * - 页面**只读**展示申请内容（按原样批准，不支持就地修改——保证回调/范围精确绑定）；
 * - 必须展示：应用名/描述/client_id、回调白名单、scopes、回跳主机、来源 IP/UA、
 *   「接入方未提供长期凭据」风险提示、「成员授权仍单独进行」提示；
 * - 批准 → 后端签发一次性安装码并返回 redirect_to → 本页整页跳转（no-referrer）。
 *
 * 未登录由路由守卫拦到登录页并带 ?redirect= 回跳（既有机制）。
 */

defineOptions({
  name: 'Oauth2Install'
});

const route = useRoute();
const { startLoading, endLoading } = useLoading();

const status = ref<'loading' | 'ready' | 'submitting' | 'error'>('loading');
const errorMsg = ref('');
const request = ref<Api.OAuth2.InstallRequestView | null>(null);

const scopeRows = computed(() =>
  (request.value?.scopes || []).map(scope => ({ scope, label: scopeLabel(scope), endpoint: scopeEndpoint(scope) }))
);

const isPending = computed(() => request.value?.status === 'PENDING');
const terminalNote = computed(() => {
  switch (request.value?.status) {
    case 'APPROVED':
      return '该申请已批准：一次性安装码已交付给接入方回调地址。若接入方未收到，请让其重新发起安装。';
    case 'REJECTED':
      return '该申请已被拒绝。';
    case 'EXPIRED':
      return '该申请已过期（15 分钟有效期）。接入方可重新发起。';
    case 'CONSUMED':
      return '该申请已完成：接入方已兑换到密钥。';
    default:
      return '';
  }
});

function getErrMsg(err: unknown, fallback: string) {
  const e = err as {
    response?: { data?: { detail?: string | { error_description?: string }; message?: string } };
    message?: string;
  } | null;
  const detail = e?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && detail.error_description) return String(detail.error_description);
  return e?.response?.data?.message || e?.message || fallback;
}

async function loadRequest() {
  const installId = String(route.params.installId || '');
  if (!installId) {
    status.value = 'error';
    errorMsg.value = '缺少安装申请编号。';
    return;
  }
  startLoading();
  const { error, data } = await fetchGetOAuthInstallRequest(installId);
  endLoading();
  if (error || !data) {
    status.value = 'error';
    errorMsg.value = getErrMsg(error, '安装申请不存在或无权查看。');
    return;
  }
  request.value = data;
  status.value = 'ready';
}

async function handleApprove() {
  if (!request.value) return;
  status.value = 'submitting';
  const { error, data } = await fetchApproveOAuthInstallRequest(request.value.install_id);
  if (error) {
    status.value = 'ready';
    window.$message?.error(getErrMsg(error, '批准失败（申请可能已被处理或过期）'));
    loadRequest();
    return;
  }
  window.$message?.success('已批准安装');
  if (data?.redirect_to) {
    // 整页跳转到接入方回调地址（携带一次性安装码与 state；后端响应头 no-referrer/no-store）
    window.location.href = data.redirect_to;
    return;
  }
  status.value = 'ready';
  loadRequest();
}

async function handleReject() {
  if (!request.value) return;
  status.value = 'submitting';
  const { error } = await fetchRejectOAuthInstallRequest(request.value.install_id);
  status.value = 'ready';
  if (error) {
    window.$message?.error(getErrMsg(error, '操作失败'));
    return;
  }
  window.$message?.success('已拒绝该安装申请');
  loadRequest();
}

onMounted(loadRequest);
</script>

<template>
  <div class="oauth2-install">
    <NSpin :show="status === 'loading'">
      <NCard class="oauth2-install__card" :bordered="false">
        <template v-if="status === 'error'">
          <h2>无法处理安装申请</h2>
          <NAlert type="error" :show-icon="false">{{ errorMsg }}</NAlert>
        </template>

        <template v-else-if="request">
          <h2 class="oauth2-install__title">确认安装</h2>
          <p class="oauth2-install__lead">
            <b>{{ request.name }}</b>
            请求接入 OpenTask。请核对以下内容后决定是否批准。
          </p>

          <NDescriptions :column="1" label-placement="left" bordered size="small" class="oauth2-install__desc">
            <NDescriptionsItem label="client_id">
              <NCode :code="request.client_id" language="text" />
            </NDescriptionsItem>
            <NDescriptionsItem v-if="request.description" label="应用描述">
              {{ request.description }}
            </NDescriptionsItem>
            <NDescriptionsItem label="安装回跳地址">
              <NCode :code="request.callback_url" language="text" word-wrap />
              <div>
                <NText depth="3">主机：</NText>
                <NTag size="small" :bordered="false">{{ request.callback_host }}</NTag>
              </div>
            </NDescriptionsItem>
            <NDescriptionsItem label="来源">
              <NText depth="3">{{ request.request_ip || '未知' }} · {{ request.user_agent || '未知 UA' }}</NText>
            </NDescriptionsItem>
            <NDescriptionsItem label="有效期至">
              {{ new Date(request.expires_at).toLocaleString('zh-CN') }}
            </NDescriptionsItem>
          </NDescriptions>

          <h3 class="oauth2-install__section">回调地址白名单（精确匹配）</h3>
          <ul class="oauth2-install__list">
            <li v-for="uri in request.redirect_uris" :key="uri">
              <NCode :code="uri" language="text" word-wrap />
            </li>
          </ul>
          <NText depth="3" class="oauth2-install__hint">
            成员授权时请求的 redirect_uri 必须与上述地址
            <b>逐字符一致</b>
            （不支持通配/尾斜杠容错）。
          </NText>

          <h3 class="oauth2-install__section">请求的权限（scopes）</h3>
          <ul class="oauth2-install__list">
            <li v-for="row in scopeRows" :key="row.scope">
              <NTag size="small" :bordered="false">{{ row.scope }}</NTag>
              {{ row.label }}
              <NText depth="3" class="oauth2-install__hint">{{ row.endpoint }}</NText>
            </li>
          </ul>
          <NText depth="3" class="oauth2-install__hint">
            scopes 是该客户端可请求权限的
            <b>上界</b>
            ；安装不会替成员授权——成员使用时仍会在授权同意页单独确认。
          </NText>

          <NAlert type="warning" :show-icon="true" class="oauth2-install__warn">
            接入方未提供长期凭据，OpenTask 无法自动验证其身份。请核对回跳主机 （{{
              request.callback_host
            }}）与来源是否可信；批准即代表信任该应用登记以上回调与权限。
          </NAlert>

          <NAlert v-if="!isPending" type="info" :show-icon="false" class="oauth2-install__warn">
            {{ terminalNote }}
          </NAlert>

          <div v-if="isPending" class="oauth2-install__actions">
            <NSpace justify="center" size="large">
              <NButton :disabled="status === 'submitting'" @click="handleReject">拒绝</NButton>
              <NButton type="primary" :loading="status === 'submitting'" @click="handleApprove">确认安装</NButton>
            </NSpace>
            <NText depth="3" class="oauth2-install__hint">
              确认后将跳转回接入方（携带一次性安装码，10 分钟内有效；密钥由接入方服务端兑换，不经浏览器）。
            </NText>
          </div>
        </template>
      </NCard>
    </NSpin>
  </div>
</template>

<style scoped>
.oauth2-install {
  display: flex;
  min-height: 100vh;
  align-items: flex-start;
  justify-content: center;
  padding: 40px 16px;
  background: var(--bg-color, #f7f8fa);
}

.oauth2-install__card {
  width: 100%;
  max-width: 720px;
  border-radius: 12px;
  box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
}

.oauth2-install__title {
  margin: 0 0 6px;
  font-size: 22px;
}

.oauth2-install__lead {
  margin: 0 0 16px;
}

.oauth2-install__desc {
  margin-bottom: 18px;
}

.oauth2-install__section {
  margin: 18px 0 8px;
  font-size: 15px;
}

.oauth2-install__list {
  margin: 0 0 6px;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.oauth2-install__hint {
  font-size: 12px;
  display: block;
  margin-bottom: 6px;
}

.oauth2-install__warn {
  margin-top: 16px;
}

.oauth2-install__actions {
  margin-top: 20px;
  text-align: center;
}

.oauth2-install__actions .oauth2-install__hint {
  margin-top: 10px;
}
</style>
