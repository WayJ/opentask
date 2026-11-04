<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { NCard, NSpace, NSpin, NSwitch, NText } from 'naive-ui';
import {
  type NotifPrefKey,
  type NotifPrefs,
  NOTIF_PREF_KEYS,
  NOTIF_PREF_LABELS,
  fetchNotifPrefs,
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

async function toggle(key: NotifPrefKey, value: boolean) {
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
  </div>
</template>
