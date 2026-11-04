<script lang="ts" setup>
import { useCommandPalette } from '@/composables/use-command-palette';
import { $t } from '@/locales';

defineOptions({ name: 'GlobalSearch' });

const { open } = useCommandPalette();
</script>

<template>
  <ButtonIcon :tooltip-content="$t('common.search')" @click="open">
    <icon-uil-search />
  </ButtonIcon>
</template>

<style lang="scss" scoped></style>
