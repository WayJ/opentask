<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { NAlert, NCard, NSpace, NSpin, NSwitch, NText } from 'naive-ui';
import {
  type NotifPrefKey,
  type NotifPrefs,
  NOTIF_PREF_KEYS,
  NOTIF_PREF_LABELS,
  fetchNotifPrefs,
  isEmailToggleDisabled,
  updateNotifPrefs
} from '@/service/api/notif-prefs';

defineOptions({ name: 'SettingsNotificationsPage' });

const loading = ref(false);
const saving = ref(false);
const prefs = ref<NotifPrefs | null>(null);

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchNotifPrefs();
    if (error) {
      window.$message?.error?.(error.message || '加载失败');
      return;
    }
    prefs.value = data as NotifPrefs;
  } finally {
    loading.value = false;
  }
}

async function toggle(key: NotifPrefKey | 'email_enabled', value: boolean) {
  if (!prefs.value) return;
  const prev = prefs.value[key];
  prefs.value = { ...prefs.value, [key]: value };
  saving.value = true;
  try {
    const { data, error } = await updateNotifPrefs({ [key]: value });
    if (error) {
      prefs.value = { ...prefs.value, [key]: prev };
      window.$message?.error?.(error.message || '保存失败');
      return;
    }
    prefs.value = data as NotifPrefs;
    window.$message?.success?.('已保存');
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="p-16px">
    <NCard title="通知偏好" :bordered="false">
      <NText depth="3" class="mb-12px block">按当前工作区生效；关闭后对应类型不再写入 Inbox（关注关系仍保留）。</NText>
      <NSpin :show="loading">
        <NSpace v-if="prefs" vertical :size="12">
          <div v-for="key in NOTIF_PREF_KEYS" :key="key" class="flex items-center justify-between py-6px">
            <NText>{{ NOTIF_PREF_LABELS[key] }}</NText>
            <NSwitch
              :value="prefs[key]"
              :disabled="saving"
              @update:value="(v: boolean) => toggle(key, v)"
            />
          </div>
        </NSpace>
        <NText v-else depth="3">加载中…</NText>
      </NSpin>
    </NCard>

    <NCard title="邮件通知" :bordered="false" class="mt-16px">
      <NAlert v-if="prefs && isEmailToggleDisabled(prefs)" type="warning" class="mb-12px" :bordered="false">
        服务器未配置 SMTP（需 SMTP_HOST 与 SMTP_FROM）。邮件通道暂不可用。
      </NAlert>
      <NText depth="3" class="mb-12px block">
        开启后，在类型偏好允许时，将同类事件额外发送到你的邮箱（username 需含 @）。默认关闭。
      </NText>
      <NSpin :show="loading">
        <div v-if="prefs" class="flex items-center justify-between py-6px">
          <NText>启用出站邮件</NText>
          <NSwitch
            :value="prefs.email_enabled"
            :disabled="saving || isEmailToggleDisabled(prefs)"
            @update:value="(v: boolean) => toggle('email_enabled', v)"
          />
        </div>
      </NSpin>
    </NCard>
  </div>
</template>
