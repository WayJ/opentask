<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import type { FormInst, FormRules } from 'naive-ui';
import { localStg } from '@/utils/storage';

const emit = defineEmits<{
  (e: 'config-save', config: { apiUrl: string; token: string }): void;
  (e: 'config-clear'): void;
}>();

// 显示配置面板
const showConfig = ref(true);

// 加载状态
const loading = ref(false);

// 表单引用
const formRef = ref<FormInst | null>(null);

// 表单数据
const formData = reactive<{
  apiUrl: string;
  token: string;
}>({
  apiUrl: '',
  token: ''
});

// 验证规则
const rules: FormRules = {
  apiUrl: [
    { required: true, message: '请输入 API URL', trigger: 'blur' },
    {
      type: 'url',
      message: '请输入有效的 URL',
      trigger: ['blur', 'input']
    }
  ],
  token: [
    { required: true, message: '请输入认证 Token', trigger: 'blur' },
    {
      min: 10,
      message: 'Token 长度至少 10 个字符',
      trigger: ['blur', 'input']
    }
  ]
};

// 是否已配置
const isConfigured = computed(() => {
  return Boolean(formData.apiUrl && formData.token);
});

// 初始化：从 localStorage 加载保存的配置
function loadSavedConfig() {
  const savedConfig = localStg.get('opentask_cli_config');
  if (savedConfig) {
    formData.apiUrl = savedConfig.apiUrl || '';
    formData.token = savedConfig.token || '';
  }
}

// 保存配置
async function handleSaveConfig() {
  try {
    loading.value = true;

    // 验证表单
    await formRef.value?.validate();

    // 保存到 localStorage
    localStg.set('opentask_cli_config', {
      apiUrl: formData.apiUrl,
      token: formData.token
    });

    // 触发父组件事件
    emit('config-save', {
      apiUrl: formData.apiUrl,
      token: formData.token
    });

    window.$message?.success('CLI 凭证配置已保存');
  } catch (error: any) {
    console.error('Failed to save config:', error);
    if (error?.errorFields) {
      window.$message?.error('请填写完整的配置信息');
    } else {
      window.$message?.error('保存配置失败');
    }
  } finally {
    loading.value = false;
  }
}

// 测试连接
async function handleTestConnection() {
  window.$message?.info('测试连接功能开发中...');
}

// 清除配置
function handleClearConfig() {
  window.$dialog?.warning({
    title: '清除配置',
    content: '确定要清除 CLI 凭证配置吗？清除后 AI 助手将无法执行命令。',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: () => {
      formData.apiUrl = '';
      formData.token = '';
      localStg.remove('opentask_cli_config');
      emit('config-clear');
      window.$message?.success('配置已清除');
    }
  });
}

// 组件挂载时加载配置
loadSavedConfig();
</script>

<template>
  <div class="cli-config-panel">
    <div class="config-header">
      <h3 class="config-title">
        <icon-mdi:keyboard-settings class="title-icon" />
        <span>OpenTask CLI 配置</span>
      </h3>
      <NButton text @click="showConfig = !showConfig">
        <template #icon>
          <icon-mdi:chevron-down v-if="!showConfig" />
          <icon-mdi:chevron-up v-else />
        </template>
      </NButton>
    </div>

    <NCollapseTransition :show="showConfig">
      <div class="config-content">
        <!-- 配置状态提示 -->
        <NAlert v-if="isConfigured" type="success" :bordered="false" class="config-status">
          <template #icon>
            <icon-mdi:check-circle />
          </template>
          CLI 凭证已配置，AI 助手将使用您的凭证执行命令
        </NAlert>

        <NAlert v-else type="warning" :bordered="false" class="config-status">
          <template #icon>
            <icon-mdi:alert-circle />
          </template>
          请配置您的 OpenTask CLI 凭证以使用 AI 助手
        </NAlert>

        <!-- 配置表单 -->
        <NForm ref="formRef" :model="formData" :rules="rules" label-placement="top" class="config-form">
          <!-- API URL -->
          <NFormItem label="API URL" path="apiUrl">
            <NInput v-model:value="formData.apiUrl" placeholder="https://api.opentask.com" :disabled="loading">
              <template #prefix>
                <icon-mdi:server-network />
              </template>
            </NInput>
            <template #feedback>
              <span class="form-feedback">您的 OpenTask 服务器地址</span>
            </template>
          </NFormItem>

          <!-- Token -->
          <NFormItem label="认证 Token" path="token">
            <NInput
              v-model:value="formData.token"
              type="password"
              show-password-on="click"
              placeholder="your-jwt-token"
              :disabled="loading"
            >
              <template #prefix>
                <icon-mdi:key-variant />
              </template>
            </NInput>
            <template #feedback>
              <span class="form-feedback">从 OpenTask 个人设置中获取</span>
            </template>
          </NFormItem>

          <!-- 操作按钮 -->
          <div class="config-actions">
            <NButton type="primary" :loading="loading" @click="handleSaveConfig">
              <template #icon>
                <icon-mdi:content-save />
              </template>
              {{ isConfigured ? '更新配置' : '保存配置' }}
            </NButton>

            <NButton v-if="isConfigured" :disabled="loading" @click="handleTestConnection">
              <template #icon>
                <icon-mdi:connection-test />
              </template>
              测试连接
            </NButton>

            <NButton v-if="isConfigured" type="error" :disabled="loading" @click="handleClearConfig">
              <template #icon>
                <icon-mdi:delete />
              </template>
              清除配置
            </NButton>
          </div>
        </NForm>

        <!-- 帮助信息 -->
        <NCollapse class="help-section">
          <NCollapseItem title="如何获取 CLI 凭证？" name="help">
            <div class="help-content">
              <ol>
                <li>登录 OpenTask 平台</li>
                <li>进入"个人设置" → "API 设置"</li>
                <li>复制 API URL 和 Token</li>
                <li>粘贴到上面的表单中</li>
              </ol>
              <NAlert type="info" :bordered="false">
                <template #icon>
                  <icon-mdi:information />
                </template>
                CLI 凭证仅用于当前会话，不会保存到服务器
              </NAlert>
            </div>
          </NCollapseItem>
        </NCollapse>
      </div>
    </NCollapseTransition>
  </div>
</template>

<style scoped>
.cli-config-panel {
  background: var(--n-color);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--n-border-color);
}

.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.config-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--n-text-color);
}

.title-icon {
  font-size: 20px;
  color: var(--n-primary-color);
}

.config-content {
  margin-top: 12px;
}

.config-status {
  margin-bottom: 16px;
}

.config-form {
  margin-bottom: 16px;
}

.form-feedback {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.config-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.help-section {
  margin-top: 16px;
}

.help-content ol {
  margin: 8px 0;
  padding-left: 20px;
}

.help-content li {
  margin-bottom: 4px;
}
</style>
