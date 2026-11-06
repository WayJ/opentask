<script setup lang="ts">
import { ref, watch } from 'vue';
import { NAlert, NButton, NCode, NModal, NSpace, NText } from 'naive-ui';

/**
 * 一次性密钥弹窗（client_secret 明文仅此一次展示）
 *
 * 安全口径（契约 §5.1）：
 * - 明文只存在于父组件的内存 ref，弹窗关闭时由父组件清空（本组件 emit close）；
 * - 不写 localStorage / sessionStorage / URL / 日志；
 * - 关闭后不可再取回，只能「轮换密钥」换新的。
 */

defineOptions({
  name: 'OAuthSecretModal'
});

const props = defineProps<{
  visible: boolean;
  /** 密钥明文（仅创建/轮换的那一次响应里出现；关闭后父组件置空） */
  secret: string;
  clientName?: string;
  /** 场景文案：创建 / 轮换 */
  scene?: 'create' | 'rotate';
}>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
}>();

const copied = ref(false);

watch(
  () => props.visible,
  value => {
    if (value) copied.value = false;
  }
);

async function handleCopy() {
  try {
    await navigator.clipboard.writeText(props.secret);
    copied.value = true;
    window.$message?.success('已复制到剪贴板');
    setTimeout(() => {
      copied.value = false;
    }, 2000);
  } catch {
    window.$message?.error('复制失败，请手动选择复制');
  }
}

function handleClose() {
  // 关闭即清空：父组件监听 update:visible 置空 secret
  emit('update:visible', false);
}
</script>

<template>
  <NModal
    :show="visible"
    preset="card"
    :title="scene === 'rotate' ? '新密钥（仅此一次）' : '客户端密钥（仅此一次）'"
    style="width: 560px"
    :mask-closable="false"
    @update:show="(v: boolean) => (v ? null : handleClose())"
  >
    <NAlert type="warning" :show-icon="true" style="margin-bottom: 16px">
      <NText strong>密钥明文只显示这一次。</NText>
      关闭本窗口后将无法再次查看（服务端只保存哈希，不含明文）。请立即复制并交给接入方安全保存；
      若丢失，只能通过「轮换密钥」重新生成。
    </NAlert>

    <div class="oauth2-secret-modal__client">
      <NText depth="3">{{ clientName ? `${clientName} · ` : '' }}client_secret</NText>
    </div>
    <NCode :code="secret" language="text" word-wrap class="oauth2-secret-modal__code" />

    <template #footer>
      <NSpace justify="end">
        <NButton @click="handleClose">我已保存，关闭</NButton>
        <NButton type="primary" :disabled="copied" @click="handleCopy">
          {{ copied ? '已复制' : '复制密钥' }}
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped>
.oauth2-secret-modal__client {
  margin-bottom: 6px;
}

.oauth2-secret-modal__code {
  padding: 12px;
  border-radius: 6px;
  font-size: 13px;
  word-break: break-all;
}
</style>
