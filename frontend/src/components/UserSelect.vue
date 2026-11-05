<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { NAvatar, NSelect, NSpace, NText } from 'naive-ui';
import { request } from '@/service/request';

interface Props {
  modelValue?: string | string[] | null;
  placeholder?: string;
  clearable?: boolean;
  disabled?: boolean;
  size?: 'small' | 'medium' | 'large';
  multiple?: boolean;
  max?: number;
}

interface PropsEmits {
  (e: 'update:modelValue', value: string | string[] | null): void;
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '选择用户',
  clearable: true,
  disabled: false,
  size: 'medium',
  multiple: false,
  max: 10
});

const emit = defineEmits<PropsEmits>();

interface SimpleUser {
  id: string;
  sso_account: string;
  sso_name: string;
}

const users = ref<SimpleUser[]>([]);
const loading = ref(false);

async function loadUsers() {
  loading.value = true;
  try {
    const response = await request<any>({
      url: '/api/users/searchable',
      method: 'get'
    });

    let userList: SimpleUser[] = [];

    if (Array.isArray(response)) {
      userList = response;
    } else if (response && response.data && Array.isArray(response.data)) {
      userList = response.data;
    }

    if (userList.length > 0) {
      users.value = userList;
    }
  } catch (error) {
    console.error('加载用户列表失败:', error);
    users.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadUsers();
});

const options = computed(() => {
  if (!users.value || users.value.length === 0) {
    return [];
  }
  return users.value.map(user => ({
    label: user.sso_name || user.sso_account,
    value: user.id,
    user
  }));
});

function handleSelect(value: string | string[] | null) {
  if (props.multiple) {
    const arr = Array.isArray(value) ? value : value ? [value] : [];
    emit('update:modelValue', arr.slice(0, props.max));
  } else {
    emit('update:modelValue', (value as string | null) ?? null);
  }
}

function getUserAvatar(user: SimpleUser): string {
  return (user.sso_name || user.sso_account || '?').charAt(0).toUpperCase();
}

function getUserLabel(user: SimpleUser): string {
  return user.sso_name || user.sso_account || '';
}

function getUserAccount(user: SimpleUser): string {
  return user.sso_account || '';
}
</script>

<template>
  <div class="user-select">
    <NSelect
      :value="modelValue"
      :options="options"
      :placeholder="placeholder"
      :clearable="clearable"
      :loading="loading"
      :size="size"
      :disabled="disabled"
      :filterable="true"
      :multiple="multiple"
      :max-tag-count="multiple ? 3 : undefined"
      :clear-filter-after-select="true"
      @update:value="handleSelect"
    >
      <template #default="{ option }">
        <div v-if="option" class="user-option">
          <NAvatar
            :size="24"
            round
            :style="{ backgroundColor: '#18a058', color: 'white', marginRight: '8px', flexShrink: 0 }"
          >
            {{ getUserAvatar(option.user) }}
          </NAvatar>
          <NSpace vertical :size="2">
            <NText style="font-size: 13px; font-weight: 500">
              {{ getUserLabel(option.user) }}
            </NText>
            <NText :depth="3" style="font-size: 11px">
              {{ getUserAccount(option.user) }}
            </NText>
          </NSpace>
        </div>
      </template>
    </NSelect>
  </div>
</template>

<style scoped>
.user-select {
  width: 100%;
}

.user-option {
  display: flex;
  align-items: center;
  padding: 4px 0;
}
</style>
