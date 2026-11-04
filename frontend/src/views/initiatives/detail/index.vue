<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  type InitiativeRow,
  type InitiativeStatus,
  fetchInitiative,
  fetchProjectList,
  fetchSetInitiativeProjects,
  fetchUpdateInitiative
} from '@/service/api';

defineOptions({ name: 'InitiativeDetailPage' });

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const saving = ref(false);
const row = ref<InitiativeRow | null>(null);
const projectOptions = ref<Array<{ label: string; value: string }>>([]);

const form = reactive({
  name: '',
  description: '',
  status: 'active' as InitiativeStatus,
  projectIds: [] as string[]
});

const id = computed(() => String(route.query.id || ''));

async function loadProjects() {
  try {
    const response = await fetchProjectList();
    const list = response.data || [];
    projectOptions.value = list.map((p: { id: string; name: string }) => ({
      label: p.name,
      value: p.id
    }));
  } catch {
    projectOptions.value = [];
  }
}

async function load() {
  if (!id.value) {
    window.$message?.warning('缺少 Initiative id');
    router.replace({ name: 'initiatives' });
    return;
  }
  loading.value = true;
  try {
    const { data, error } = await fetchInitiative(id.value);
    if (error || !data) {
      window.$message?.error(error?.message || '加载失败');
      return;
    }
    row.value = data;
    form.name = data.name;
    form.description = data.description || '';
    form.status = data.status;
    form.projectIds = [...(data.projectIds || [])];
  } finally {
    loading.value = false;
  }
}

async function onSave() {
  if (!id.value) return;
  const name = form.name.trim();
  if (!name) {
    window.$message?.warning('请输入名称');
    return;
  }
  saving.value = true;
  try {
    const { error: e1 } = await fetchUpdateInitiative(id.value, {
      name,
      description: form.description,
      status: form.status
    });
    if (e1) {
      window.$message?.error(e1.message || '保存失败');
      return;
    }
    const { data, error: e2 } = await fetchSetInitiativeProjects(id.value, form.projectIds);
    if (e2) {
      window.$message?.error(e2.message || '更新关联项目失败');
      return;
    }
    if (data) {
      row.value = data;
      form.projectIds = [...(data.projectIds || [])];
    }
    window.$message?.success('已保存');
  } finally {
    saving.value = false;
  }
}

watch(id, () => {
  load();
});

onMounted(async () => {
  await loadProjects();
  await load();
});
</script>

<template>
  <div class="h-full flex-col gap-16px overflow-auto p-16px">
    <div class="flex items-center gap-12px">
      <NButton quaternary @click="router.push({ name: 'initiatives' })">← 返回列表</NButton>
      <h2 class="text-18px font-600">Initiative 详情</h2>
    </div>

    <NSpin :show="loading">
      <NCard v-if="row" :bordered="false" title="基本信息">
        <NForm label-placement="left" label-width="100" class="max-w-640px">
          <NFormItem label="名称" required>
            <NInput v-model:value="form.name" maxlength="100" />
          </NFormItem>
          <NFormItem label="描述">
            <NInput v-model:value="form.description" type="textarea" :rows="4" />
          </NFormItem>
          <NFormItem label="状态">
            <NSelect
              v-model:value="form.status"
              :options="[
                { label: '计划中', value: 'planned' },
                { label: '进行中', value: 'active' },
                { label: '已完成', value: 'completed' },
                { label: '已取消', value: 'canceled' }
              ]"
            />
          </NFormItem>
          <NFormItem label="关联项目">
            <NSelect
              v-model:value="form.projectIds"
              multiple
              filterable
              clearable
              placeholder="选择同工作区 Project"
              :options="projectOptions"
            />
          </NFormItem>
          <NFormItem>
            <NButton type="primary" :loading="saving" @click="onSave">保存</NButton>
          </NFormItem>
        </NForm>
        <p class="mt-8px text-12px text-gray-400">文档与健康汇总将在后续 Sprint；此处仅 Project 关联。</p>
      </NCard>
    </NSpin>
  </div>
</template>
