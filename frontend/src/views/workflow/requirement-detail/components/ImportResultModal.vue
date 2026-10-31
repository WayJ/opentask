<script setup lang="ts">
import { computed } from 'vue';
import { NAlert, NButton, NModal, NSpace } from 'naive-ui';

interface ImportResult {
  imported_count: number;
  failed_count: number;
  errors: string[];
}

interface Props {
  show: boolean;
  result: ImportResult | null;
}

interface Emits {
  (e: 'update:show', value: boolean): void;
}

const props = withDefaults(defineProps<Props>(), {
  show: false,
  result: null
});

const emit = defineEmits<Emits>();

const localShow = computed({
  get: () => props.show,
  set: value => emit('update:show', value)
});

const alertType = computed(() => (props.result?.failed_count && props.result.failed_count > 0 ? 'warning' : 'success'));
</script>

<template>
  <NModal v-model:show="localShow" preset="card" title="导入结果" style="width: 500px">
    <NAlert v-if="result" :type="alertType">
      <template #header>导入完成</template>
      <p>成功导入 {{ result.imported_count }} 个任务</p>
      <p v-if="result.failed_count > 0">失败 {{ result.failed_count }} 个任务</p>
    </NAlert>
    <div v-if="result && result.errors.length > 0" style="margin-top: 16px">
      <p style="font-weight: bold; margin-bottom: 8px">错误详情:</p>
      <ul style="max-height: 200px; overflow-y: auto">
        <li v-for="(error, index) in result.errors" :key="index" style="color: #d03050; font-size: 12px">
          {{ error }}
        </li>
      </ul>
    </div>
    <template #footer>
      <NSpace justify="end">
        <NButton type="primary" @click="localShow = false">关闭</NButton>
      </NSpace>
    </template>
  </NModal>
</template>
