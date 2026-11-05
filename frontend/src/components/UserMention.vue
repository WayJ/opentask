<script setup lang="ts">
import { computed } from 'vue';
import { NTag } from 'naive-ui';

defineOptions({ name: 'UserMention' });

const props = withDefaults(
  defineProps<{
    username: string;
    userId?: string | null;
    size?: 'tiny' | 'small' | 'medium';
  }>(),
  { userId: null, size: 'small' }
);

const label = computed(() => `@${(props.username || '').replace(/^@/, '')}`);
</script>

<template>
  <NTag class="user-mention" :size="size" round :bordered="false" type="info" :data-user-id="userId || undefined">
    {{ label }}
  </NTag>
</template>

<style scoped>
.user-mention {
  vertical-align: middle;
  cursor: default;
}
</style>
