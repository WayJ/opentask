<script setup lang="tsx">
import { computed, onMounted, ref } from 'vue';
import { NAlert, NButton, NCode, NDataTable, NPopconfirm, NSpace, NTabPane, NTabs, NTag, NText } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { useLoading } from '@sa/hooks';
import {
  fetchApproveOAuthInstallRequest,
  fetchDeleteOAuthClient,
  fetchGetOAuthClients,
  fetchListOAuthInstallRequests,
  fetchRejectOAuthInstallRequest,
  fetchRotateOAuthClientSecret,
  fetchUpdateOAuthClient
} from '@/service/api';
import { clientStatusLabel, installStatusLabel, scopeLabel } from '@/utils/oauth2-client';
import type { Api } from '@/typings/api';
import ClientFormDrawer from './modules/client-form-drawer.vue';
import SecretModal from './modules/secret-modal.vue';
import GuidePanel from './modules/guide-panel.vue';

/**
 * OAuth 客户端管理（管理员）
 *
 * 三个页签：
 * - 客户端：列表 / 新建 / 编辑 / 启停 / 轮换密钥 / 删除（密钥明文仅创建/轮换时一次性展示）
 * - 安装申请：自动接入（Install Flow）的审计列表——状态、来源、时间
 * - 接入说明：小蓝 CoWork 两条接入路径 + 协议端点清单
 *
 * 权限：路由受 menu 权限 route_key=manage_oauth2 门禁（admin 专属）；
 * 后端 API 一律要求 role=admin，页面绕过也 403。
 */

defineOptions({
  name: 'ManageOauth2'
});

const { loading, startLoading, endLoading } = useLoading();

// ===== 客户端列表 =====
const clients = ref<Api.OAuth2.OAuthClient[]>([]);

async function loadClients() {
  startLoading();
  const { error, data } = await fetchGetOAuthClients();
  if (!error && data) {
    clients.value = data;
  } else {
    window.$message?.error('加载客户端列表失败');
  }
  endLoading();
}

function renderStatus(status: string) {
  const enabled = status === 'ACTIVE';
  return (
    <span class={`vk-status ${enabled ? 'vk-status--success' : 'vk-status--muted'}`}>
      <i class="vk-status__dot" />
      {clientStatusLabel(status)}
    </span>
  );
}

function renderScopes(row: Api.OAuth2.OAuthClient) {
  const scopes = row.scopes || [];
  if (!scopes.length) return <span class="vk-muted-text">未配置</span>;
  return (
    <NSpace size={4} wrap={false} align="center">
      {scopes.map(scope => (
        <span key={scope} class="vk-role-tag" title={scopeLabel(scope)}>
          {scope}
        </span>
      ))}
    </NSpace>
  );
}

// ===== 表单抽屉 / 一次性密钥 =====
const formVisible = ref(false);
const editingClient = ref<Api.OAuth2.OAuthClient | null>(null);
const secretVisible = ref(false);
const secretText = ref('');
const secretClientName = ref('');
const secretScene = ref<'create' | 'rotate'>('create');

function openCreate() {
  editingClient.value = null;
  formVisible.value = true;
}

function openEdit(row: Api.OAuth2.OAuthClient) {
  editingClient.value = row;
  formVisible.value = true;
}

function handleFormSubmitted(secret?: string, clientName?: string) {
  if (secret) {
    secretText.value = secret;
    secretClientName.value = clientName || '';
    secretScene.value = 'create';
    secretVisible.value = true;
  }
  loadClients();
}

async function handleRotate(row: Api.OAuth2.OAuthClient) {
  const { error, data } = await fetchRotateOAuthClientSecret(row.client_id);
  if (error) {
    window.$message?.error('轮换失败');
    return;
  }
  secretText.value = data?.client_secret || '';
  secretClientName.value = row.name;
  secretScene.value = 'rotate';
  secretVisible.value = true;
  loadClients();
}

function handleSecretClosed(visible: boolean) {
  secretVisible.value = visible;
  if (!visible) {
    // 关闭即清空：内存中不留密钥明文
    secretText.value = '';
    secretClientName.value = '';
  }
}

async function toggleStatus(row: Api.OAuth2.OAuthClient) {
  const next = row.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
  const { error } = await fetchUpdateOAuthClient(row.client_id, { status: next });
  if (error) {
    window.$message?.error(next === 'DISABLED' ? '停用失败' : '启用失败');
    return;
  }
  window.$message?.success(next === 'DISABLED' ? '已停用（其授权请求与换 token 一律拒绝）' : '已启用');
  loadClients();
}

async function handleDelete(row: Api.OAuth2.OAuthClient) {
  const { error } = await fetchDeleteOAuthClient(row.client_id);
  if (error) {
    window.$message?.error('删除失败');
    return;
  }
  window.$message?.success('已删除（其授权码与令牌已级联吊销）');
  loadClients();
}

const clientColumns: DataTableColumns<Api.OAuth2.OAuthClient> = [
  {
    title: '应用',
    key: 'name',
    minWidth: 200,
    render: row => (
      <div>
        <NText>{row.name}</NText>
        <div>
          <NText depth={3} code>
            {row.client_id}
          </NText>
        </div>
      </div>
    )
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: row => renderStatus(row.status)
  },
  {
    title: '回调地址',
    key: 'redirect_uris',
    minWidth: 220,
    render: row => (
      <div>
        {row.redirect_uris.map(uri => (
          <div key={uri} class="oauth2-page__uri" title={uri}>
            {uri}
          </div>
        ))}
      </div>
    )
  },
  {
    title: '授权范围',
    key: 'scopes',
    minWidth: 200,
    render: renderScopes
  },
  {
    title: '密钥前缀',
    key: 'secret_prefix',
    width: 130,
    render: row => <NCode code={`${row.secret_prefix}…`} language="text" />
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 110,
    render: row => <NText depth={3}>{row.created_at ? new Date(row.created_at).toLocaleDateString('zh-CN') : ''}</NText>
  },
  {
    title: '操作',
    key: 'actions',
    width: 240,
    render: row => (
      <NSpace size={4} wrap={false}>
        <NButton size="small" quaternary onClick={() => openEdit(row)}>
          编辑
        </NButton>
        <NButton size="small" quaternary onClick={() => toggleStatus(row)}>
          {row.status === 'ACTIVE' ? '停用' : '启用'}
        </NButton>
        <NPopconfirm onPositiveClick={() => handleRotate(row)}>
          {{
            default: () => '轮换后旧密钥立即失效，确定继续？',
            trigger: () => (
              <NButton size="small" quaternary type="warning">
                轮换密钥
              </NButton>
            )
          }}
        </NPopconfirm>
        <NPopconfirm onPositiveClick={() => handleDelete(row)}>
          {{
            default: () => '删除将级联吊销其授权码与令牌，确定？',
            trigger: () => (
              <NButton size="small" quaternary type="error">
                删除
              </NButton>
            )
          }}
        </NPopconfirm>
      </NSpace>
    )
  }
];

// ===== 安装申请（审计） =====
const installLoading = ref(false);
const installRequests = ref<Api.OAuth2.InstallRequestView[]>([]);

async function loadInstallRequests() {
  installLoading.value = true;
  const { error, data } = await fetchListOAuthInstallRequests(50);
  if (!error && data) {
    installRequests.value = data;
  }
  installLoading.value = false;
}

async function handleApproveInstall(row: Api.OAuth2.InstallRequestView) {
  const { error, data } = await fetchApproveOAuthInstallRequest(row.install_id);
  if (error) {
    window.$message?.error('批准失败（申请可能已被处理或过期）');
    loadInstallRequests();
    return;
  }
  window.$message?.success('已批准：安装码已通过浏览器回跳交付给接入方');
  if (data?.redirect_to) {
    // 整页跳转到接入方回调地址（带一次性安装码与 state）
    window.location.href = data.redirect_to;
    return;
  }
  loadInstallRequests();
}

async function handleRejectInstall(row: Api.OAuth2.InstallRequestView) {
  const { error } = await fetchRejectOAuthInstallRequest(row.install_id);
  if (error) {
    window.$message?.error('操作失败');
    return;
  }
  window.$message?.success('已拒绝');
  loadInstallRequests();
}

function renderInstallStatus(status: string) {
  const map: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
    PENDING: 'warning',
    APPROVED: 'info',
    REJECTED: 'error',
    EXPIRED: 'default',
    CONSUMED: 'success'
  };
  return (
    <NTag size="small" type={map[status] || 'default'}>
      {installStatusLabel(status)}
    </NTag>
  );
}

const installColumns: DataTableColumns<Api.OAuth2.InstallRequestView> = [
  {
    title: '应用',
    key: 'name',
    minWidth: 180,
    render: row => (
      <div>
        <NText>{row.name}</NText>
        <div>
          <NText depth={3} code>
            {row.client_id}
          </NText>
        </div>
      </div>
    )
  },
  {
    title: '状态',
    key: 'status',
    width: 180,
    render: row => renderInstallStatus(row.status)
  },
  {
    title: '回调主机',
    key: 'callback_host',
    minWidth: 160,
    render: row => <NText depth={2}>{row.callback_host}</NText>
  },
  {
    title: '来源 IP',
    key: 'request_ip',
    width: 130,
    render: row => <NText depth={3}>{row.request_ip || '—'}</NText>
  },
  {
    title: '申请时间',
    key: 'created_at',
    width: 150,
    render: row => <NText depth={3}>{row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : ''}</NText>
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: row =>
      row.status === 'PENDING' ? (
        <NSpace size={4} wrap={false}>
          <NButton size="small" type="primary" secondary onClick={() => handleApproveInstall(row)}>
            批准
          </NButton>
          <NButton size="small" quaternary type="error" onClick={() => handleRejectInstall(row)}>
            拒绝
          </NButton>
        </NSpace>
      ) : (
        <NButton size="small" quaternary onClick={() => openInstallPage(row.install_id)}>
          打开确认页
        </NButton>
      )
  }
];

function openInstallPage(installId: string) {
  window.open(`/oauth2/install/${installId}`, '_blank');
}

const pendingCount = computed(() => installRequests.value.filter(item => item.status === 'PENDING').length);

onMounted(() => {
  loadClients();
  loadInstallRequests();
});
</script>

<template>
  <div class="oauth2-page">
    <div class="oauth2-page__header">
      <div>
        <h2 class="oauth2-page__title">OAuth 客户端</h2>
        <NText depth="3">
          管理接入 OpenTask 的 OAuth 客户端（如小蓝 CoWork）。密钥只在创建/轮换时显示一次；成员授权仍单独进行。
        </NText>
      </div>
      <NButton type="primary" @click="openCreate">新建客户端</NButton>
    </div>

    <NTabs type="line" animated default-value="clients">
      <NTabPane name="clients" tab="客户端">
        <NAlert type="info" :show-icon="false" style="margin-bottom: 12px">
          client_secret 仅在创建/轮换时显示一次（服务端只存哈希）；redirect_uris 与授权请求
          <b>逐字符精确匹配</b>
          。
        </NAlert>
        <NDataTable
          :columns="clientColumns"
          :data="clients"
          :loading="loading"
          :bordered="false"
          striped
          :row-key="(row: Api.OAuth2.OAuthClient) => row.client_id"
        />
      </NTabPane>

      <NTabPane name="installs" :tab="`安装申请${pendingCount ? ` (${pendingCount})` : ''}`">
        <NAlert type="info" :show-icon="false" style="margin-bottom: 12px">
          自动接入（小蓝发起安装）的申请记录。批准即签发一次性安装码并回跳给接入方；密钥由接入方服务端用 verifier 兑换，
          <b>不经浏览器</b>
          。
        </NAlert>
        <NDataTable
          :columns="installColumns"
          :data="installRequests"
          :loading="installLoading"
          :bordered="false"
          striped
          :row-key="(row: Api.OAuth2.InstallRequestView) => row.install_id"
        />
      </NTabPane>

      <NTabPane name="guide" tab="接入说明">
        <GuidePanel />
      </NTabPane>
    </NTabs>

    <ClientFormDrawer v-model:visible="formVisible" :client="editingClient" @submitted="handleFormSubmitted" />
    <SecretModal
      :visible="secretVisible"
      :secret="secretText"
      :client-name="secretClientName"
      :scene="secretScene"
      @update:visible="handleSecretClosed"
    />
  </div>
</template>

<style scoped>
.oauth2-page {
  padding: 16px;
}

.oauth2-page__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 16px;
}

.oauth2-page__title {
  margin: 0 0 4px;
  font-size: 20px;
}

.oauth2-page__uri {
  font-size: 12px;
  color: var(--n-text-color-disabled, #999);
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
