<script setup lang="ts">
import logoUrl from '@/assets/imgs/opentask-logo.png';

defineOptions({ name: 'SystemLogo' });
</script>

<template>
  <img class="app-logo" :src="logoUrl" alt="OpenTask" width="100%" height="100%" draggable="false" />
</template>

<style scoped>
.app-logo {
  display: block;
  object-fit: contain;
  border-radius: 22%;
}
</style>
