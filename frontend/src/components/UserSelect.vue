<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { NAvatar, NSelect, NSpace, NText } from 'naive-ui';
import { request } from '@/service/request';

interface Props {
  modelValue?: string | null;
  placeholder?: string;
  clearable?: boolean;
  disabled?: boolean;
  size?: 'small' | 'medium' | 'large';
}

interface PropsEmits {
  (e: 'update:modelValue', value: string | null): void;
}

withDefaults(defineProps<Props>(), {
  placeholder: '选择用户',
  clearable: true,
  disabled: false,
  size: 'medium'
});

defineEmits<PropsEmits>();

// 用户列表（使用简化的类型）
interface SimpleUser {
  id: string;
  jnpf_account: string;
  jnpf_name: string;
}

const users = ref<SimpleUser[]>([]);
const loading = ref(false);

// 加载用户列表（使用不需要权限的端点）
async function loadUsers() {
  loading.value = true;
  try {
    const response = await request<any>({
      url: '/api/users/searchable',
      method: 'get'
    });

    // 处理不同的响应格式
    let userList: SimpleUser[] = [];

    if (Array.isArray(response)) {
      // 直接是数组
      userList = response;
    } else if (response && response.data && Array.isArray(response.data)) {
      // 响应格式：{data: [...], error: null}
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

// 初始化时加载用户
onMounted(() => {
  loadUsers();
});

// 选项列表
const options = computed(() => {
  if (!users.value || users.value.length === 0) {
    return [];
  }
  return users.value.map(user => ({
    label: user.jnpf_name || user.jnpf_account,
    value: user.id,
    user
  }));
});

// 处理选择
function handleSelect(value: string | null) {
  emit('update:modelValue', value);
}

// 获取用户头像文字
function getUserAvatar(user: SimpleUser): string {
  return (user.jnpf_name || user.jnpf_account || '?').charAt(0).toUpperCase();
}

// 获取用户显示名称
function getUserLabel(user: SimpleUser): string {
  return user.jnpf_name || user.jnpf_account || '';
}

// 获取用户账号
function getUserAccount(user: SimpleUser): string {
  return user.jnpf_account || '';
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
