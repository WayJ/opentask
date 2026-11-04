<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { NAlert, NCard, NSpace, NSpin, NSwitch, NText } from 'naive-ui';
import {
  type NotifChannelKey,
  type NotifPrefKey,
  type NotifPrefs,
  NOTIF_PREF_LABELS,
  NOTIF_PREF_LIST_KEYS,
  fetchNotifPrefs,
  isDigestToggleDisabled,
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

async function toggle(key: NotifPrefKey | NotifChannelKey, value: boolean) {
  if (!prefs.value) return;
  const prev = prefs.value[key];
  prefs.value = { ...prefs.value, [key]: value };
  // Turning off due_reminder also clears digest locally for UX
  if (key === 'due_reminder' && !value && prefs.value.due_reminder_digest) {
    prefs.value = { ...prefs.value, due_reminder_digest: false };
  }
  saving.value = true;
  try {
    const body: Partial<Record<NotifPrefKey | NotifChannelKey, boolean>> = { [key]: value };
    if (key === 'due_reminder' && !value) {
      body.due_reminder_digest = false;
    }
    const { data, error } = await updateNotifPrefs(body);
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
          <div v-for="key in NOTIF_PREF_LIST_KEYS" :key="key" class="flex items-center justify-between py-6px">
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

    <NCard title="到期提醒" :bordered="false" class="mt-16px">
      <NText depth="3" class="mb-12px block">
        按工作区时区日历日扫描（未设时区则 UTC）；即将到期 = 今日起 3 日内；逾期每日至多一条。时区可在 SLA / 工作区设置中配置。邮件仍受「启用出站邮件」与 SMTP 约束。外部调度
        <code>POST /api/inbox/run-due-reminders</code>，无内置 cron。
      </NText>
      <NSpin :show="loading">
        <NSpace v-if="prefs" vertical :size="12">
          <div class="flex items-center justify-between py-6px">
            <NText>到期提醒</NText>
            <NSwitch
              :value="prefs.due_reminder"
              :disabled="saving"
              @update:value="(v: boolean) => toggle('due_reminder', v)"
            />
          </div>
          <div class="flex items-center justify-between py-6px">
            <NText>合并为每日摘要</NText>
            <NSwitch
              :value="prefs.due_reminder_digest"
              :disabled="saving || isDigestToggleDisabled(prefs)"
              @update:value="(v: boolean) => toggle('due_reminder_digest', v)"
            />
          </div>
        </NSpace>
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
