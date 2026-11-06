<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { NButton, NCard, NInput, NSpace, NSpin, NTag, NText } from 'naive-ui';
import {
  type PublicRequestStatusCard,
  fetchPublicRequestStatus,
  submitPublicRequestReply
} from '@/service/api/customer-requests';

defineOptions({ name: 'PublicRequestStatusPage' });

const route = useRoute();
const token = computed(() => String(route.params.token || ''));
const loading = ref(true);
const submitting = ref(false);
const card = ref<PublicRequestStatusCard | null>(null);
const errorMsg = ref('');
const replyBody = ref('');
const replyOk = ref(false);

async function load() {
  loading.value = true;
  errorMsg.value = '';
  replyOk.value = false;
  try {
    if (!token.value) {
      errorMsg.value = '无效链接';
      return;
    }
    card.value = await fetchPublicRequestStatus(token.value);
  } catch (e: any) {
    errorMsg.value = e?.message || '状态页不存在或已撤销';
    card.value = null;
  } finally {
    loading.value = false;
  }
}

async function onReply() {
  if (!card.value?.publicRepliesEnabled) return;
  const body = replyBody.value.trim();
  if (!body) return;
  submitting.value = true;
  try {
    await submitPublicRequestReply(token.value, body);
    replyOk.value = true;
    replyBody.value = '';
    await load();
  } catch (e: any) {
    window.$message?.error?.(e?.message || '提交失败');
  } finally {
    submitting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="ot-public-page min-h-screen">
    <NCard title="请求状态" :bordered="false" class="ot-public-card card-wrapper">
      <NSpin :show="loading">
        <div v-if="errorMsg" class="py-6 text-center text-red-500">{{ errorMsg }}</div>
        <div v-else-if="card">
          <div class="mb-3 text-lg font-medium">{{ card.title }}</div>
          <NSpace class="mb-3">
            <NTag type="info">{{ card.status }}</NTag>
            <NTag v-if="card.priority" size="small">{{ card.priority }}</NTag>
          </NSpace>
          <NText depth="3" class="block mb-2">客户：{{ card.customerName || '—' }}</NText>
          <NText depth="3" class="block mb-2">更新：{{ card.updatedAt || '—' }}</NText>
          <NText depth="3" class="block mb-4">
            关联问题：
            <span v-if="card.linkedIssueCodes?.length">{{ card.linkedIssueCodes.join(', ') }}</span>
            <span v-else>{{ card.linkedIssueCount || 0 }}</span>
          </NText>

          <div v-if="card.recentPublicReplies?.length" class="mb-4">
            <div class="mb-2 text-sm font-medium">近期留言</div>
            <div
              v-for="(r, idx) in card.recentPublicReplies"
              :key="idx"
              class="mb-2 rounded bg-gray-100 p-2 text-sm dark:bg-gray-800"
            >
              <div>{{ r.body }}</div>
              <NText depth="3" class="text-xs">{{ r.createdAt }}</NText>
            </div>
          </div>

          <div v-if="card.publicRepliesEnabled">
            <div v-if="replyOk" class="mb-2 text-green-600 text-sm">已提交留言</div>
            <NInput v-model:value="replyBody" type="textarea" :rows="3" placeholder="留言给团队…" class="mb-2" />
            <NButton type="primary" :loading="submitting" @click="onReply">发送留言</NButton>
          </div>
        </div>
      </NSpin>
    </NCard>
  </div>
</template>
