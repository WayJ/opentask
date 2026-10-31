<!-- frontend/src/components/shared/Card/BaseCard.vue -->
<script setup lang="ts">
interface Props {
  hoverable?: boolean;
  clickable?: boolean;
  bordered?: boolean;
}

withDefaults(defineProps<Props>(), {
  hoverable: false,
  clickable: false,
  bordered: true
});

const emit = defineEmits<{
  click: [];
}>();

const handleClick = () => {
  emit('click');
};
</script>

<template>
  <div
    class="base-card"
    :class="[
      {
        'base-card--hoverable': hoverable,
        'base-card--clickable': clickable,
        'base-card--bordered': bordered
      }
    ]"
    @click="handleClick"
  >
    <slot />
  </div>
</template>

<style scoped>
.base-card {
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
  box-shadow: var(--shadow-sm);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.base-card--bordered {
  border: 1px solid var(--color-border-subtle);
}

.base-card--hoverable:hover {
  box-shadow: var(--shadow-md);
}

.base-card--clickable {
  cursor: pointer;
}

.base-card--clickable:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}
</style>
