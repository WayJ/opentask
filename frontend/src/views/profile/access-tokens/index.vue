<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import {
  NAlert,
  NButton,
  NCode,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NInputGroup,
  NModal,
  NPopconfirm,
  NSpace,
  NTag,
  NText
} from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import type { AccessToken, AccessTokenWithToken } from '@/service/api/access-token';
import { useAccessTokenStore } from '@/store/modules/access-token';

defineOptions({
  name: 'AccessTokens'
});

const tokenStore = useAccessTokenStore();
const loading = ref(false);
const showCreateModal = ref(false);
const showTokenModal = ref(false);
const createdToken = ref<AccessTokenWithToken | null>(null);
const copied = ref(false);

// Form data
const formData = reactive({
  name: '',
  description: ''
});

// Table columns
const columns: DataTableColumns<AccessToken> = [
  {
    title: '名称',
    key: 'name',
    width: 180
  },
  {
    title: '描述',
    key: 'description',
    width: 200,
    render: row => {
      return h(NText, { depth: row.description ? undefined : 3 }, row.description || '无描述');
    }
  },
  {
    title: 'Token 前缀',
    key: 'token_prefix',
    width: 120,
    render: row => {
      return h(NCode, { language: 'text' }, { default: () => `${row.token_prefix}...` });
    }
  },
  {
    title: '过期时间',
    key: 'expires_at',
    width: 180,
    render: row => {
      const expired = new Date(row.expires_at) < new Date();
      return h(
        NTag,
        { type: expired ? 'error' : 'success', size: 'small' },
        expired ? '已过期' : new Date(row.expires_at).toLocaleDateString('zh-CN')
      );
    }
  },
  {
    title: '最后使用',
    key: 'last_used_at',
    width: 180,
    render: row => {
      if (!row.last_used_at) return h(NText, { depth: 3 }, '未使用');
      return h(NText, {}, new Date(row.last_used_at).toLocaleString('zh-CN'));
    }
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render: row => {
      return h(NText, {}, new Date(row.created_at).toLocaleString('zh-CN'));
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render: row => {
      return h(
        NPopconfirm,
        {
          onPositiveClick: () => handleDelete(row)
        },
        {
          default: () => '确定要删除此 Token 吗？删除后使用该 Token 的应用将无法继续访问。',
          trigger: () => h(NButton, { size: 'small', type: 'error' }, '删除')
        }
      );
    }
  }
];

// Load tokens
async function loadTokens() {
  loading.value = true;
  try {
    await tokenStore.loadTokens();
  } finally {
    loading.value = false;
  }
}

// Create token
async function handleCreate() {
  try {
    const result = await tokenStore.createToken({
      name: formData.name,
      description: formData.description || undefined
    });
    createdToken.value = result;
    showCreateModal.value = false;
    showTokenModal.value = true;
    resetForm();
  } catch {
    window.$message?.error('Token 创建失败');
  }
}

// Delete token
async function handleDelete(token: AccessToken) {
  try {
    await tokenStore.removeToken(token.id);
    window.$message?.success('Token 已删除');
  } catch {
    window.$message?.error('Token 删除失败');
  }
}

// Copy token to clipboard
async function copyToken() {
  if (!createdToken.value?.token) return;
  try {
    await navigator.clipboard.writeText(createdToken.value.token);
    copied.value = true;
    window.$message?.success('已复制到剪贴板');
    setTimeout(() => {
      copied.value = false;
    }, 2000);
  } catch {
    window.$message?.error('复制失败，请手动复制');
  }
}

// Open create modal
function openCreateModal() {
  resetForm();
  showCreateModal.value = true;
}

// Reset form
function resetForm() {
  formData.name = '';
  formData.description = '';
}

onMounted(() => {
  loadTokens();
});
</script>

<template>
  <div class="access-tokens-page">
    <div class="page-header">
      <h2>Access Token 管理</h2>
      <NButton type="primary" @click="openCreateModal">创建 Token</NButton>
    </div>

    <NAlert type="info" style="margin-bottom: 16px">
      Access Token 用于 CLI 工具认证，有效期默认 1 年。创建后请妥善保管，Token 值仅在创建时显示一次。
    </NAlert>

    <NDataTable :columns="columns" :data="tokenStore.tokens" :loading="loading" :bordered="false" striped />

    <!-- Create Token Modal -->
    <NModal v-model:show="showCreateModal" preset="card" title="创建 Access Token" style="width: 500px">
      <NForm :model="formData" label-placement="left" label-width="80px" style="margin-top: 24px">
        <NFormItem label="名称" path="name" :rule="{ required: true, message: '请输入 Token 名称' }">
          <NInput v-model:value="formData.name" placeholder="例如：开发环境 CLI" />
        </NFormItem>

        <NFormItem label="描述" path="description">
          <NInput v-model:value="formData.description" type="textarea" placeholder="可选，描述 Token 用途" :rows="3" />
        </NFormItem>

        <NFormItem label="有效期">
          <NText depth="3">1 年（固定，不可修改）</NText>
        </NFormItem>
      </NForm>

      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCreateModal = false">取消</NButton>
          <NButton type="primary" :disabled="!formData.name" @click="handleCreate">创建</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Show Created Token Modal -->
    <NModal
      v-model:show="showTokenModal"
      preset="card"
      title="Token 创建成功"
      style="width: 600px"
      :closable="false"
      :mask-closable="false"
    >
      <NAlert type="warning" style="margin-bottom: 16px">
        请立即复制并妥善保存此 Token。关闭此对话框后将无法再次查看！
      </NAlert>

      <div v-if="createdToken" style="margin: 16px 0">
        <div style="margin-bottom: 12px">
          <NText strong>Token 名称：</NText>
          <NText>{{ createdToken.name }}</NText>
        </div>
        <div style="margin-bottom: 12px">
          <NText strong>Token 值：</NText>
        </div>
        <NInputGroup>
          <NInput :value="createdToken.token" readonly type="textarea" :rows="3" style="font-family: monospace" />
          <NButton type="primary" style="height: auto" @click="copyToken">
            {{ copied ? '已复制' : '复制' }}
          </NButton>
        </NInputGroup>
        <div style="margin-top: 12px">
          <NText depth="3" style="font-size: 12px">
            在 CLI 中使用：
            <NText code>opentask config set-access-token {token}</NText>
          </NText>
        </div>
      </div>

      <template #footer>
        <NSpace justify="end">
          <NButton type="primary" @click="showTokenModal = false">我已保存，关闭</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.access-tokens-page {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
}
</style>
