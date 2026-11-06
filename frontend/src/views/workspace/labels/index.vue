<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { type DataTableColumns, NButton, NCard, NColorPicker, NDataTable, NInput, NSpace, NTag } from 'naive-ui';
import { type TagGroupItem, type TagItem, tagApi } from '@/service/api/tag';

defineOptions({ name: 'WorkspaceLabelsPage' });

const loading = ref(false);
const tags = ref<TagItem[]>([]);
const groups = ref<TagGroupItem[]>([]);
const creating = ref(false);
const form = reactive({
  name: '',
  color: '#3b82f6',
  groupId: null as string | null
});
const groupForm = reactive({ name: '', color: '#94a3b8' });

const groupName = computed(() => {
  const map = new Map(groups.value.map(g => [g.id, g.name]));
  return (id?: string | null) => (id ? map.get(id) || id : '未分组');
});

const columns: DataTableColumns<TagItem> = [
  {
    title: '标签',
    key: 'name',
    render: row =>
      h(
        NTag,
        { size: 'small', bordered: false, style: { background: row.color, color: '#fff' } },
        { default: () => row.name }
      )
  },
  {
    title: '颜色',
    key: 'color',
    width: 120,
    render: row => row.color
  },
  {
    title: '分组',
    key: 'groupId',
    render: row => groupName.value(row.groupId)
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: row =>
      h(
        NButton,
        {
          size: 'tiny',
          tertiary: true,
          type: 'error',
          onClick: () => removeTag(row.id)
        },
        { default: () => '删除' }
      )
  }
];

async function load() {
  loading.value = true;
  try {
    const [t, g] = await Promise.all([tagApi.list(), tagApi.listGroups()]);
    tags.value = t.data?.rows || [];
    groups.value = g.data?.rows || [];
  } finally {
    loading.value = false;
  }
}

async function createTag() {
  if (!form.name.trim()) {
    window.$message?.warning?.('请输入标签名');
    return;
  }
  creating.value = true;
  try {
    const { error } = await tagApi.create({
      name: form.name.trim(),
      color: form.color,
      group_id: form.groupId || undefined
    });
    if (error) {
      window.$message?.error?.(error.message || '创建失败');
      return;
    }
    form.name = '';
    window.$message?.success?.('标签已创建');
    await load();
  } finally {
    creating.value = false;
  }
}

async function createGroup() {
  if (!groupForm.name.trim()) {
    window.$message?.warning?.('请输入分组名');
    return;
  }
  const { error } = await tagApi.createGroup({
    name: groupForm.name.trim(),
    color: groupForm.color
  });
  if (error) {
    window.$message?.error?.(error.message || '创建分组失败');
    return;
  }
  groupForm.name = '';
  window.$message?.success?.('分组已创建');
  await load();
}

async function removeTag(id: number) {
  const { error } = await tagApi.remove(id);
  if (error) {
    window.$message?.error?.(error.message || '删除失败');
    return;
  }
  window.$message?.success?.('已删除');
  await load();
}

onMounted(load);
</script>

<template>
  <div class="h-full flex-col-stretch gap-12px overflow-hidden lt-sm:overflow-auto">
    <NCard title="标签" :bordered="false" class="card-wrapper sm:flex-1-hidden">
      <NSpace vertical :size="16">
        <NSpace>
          <NInput v-model:value="form.name" placeholder="新标签名" style="width: 180px" />
          <NColorPicker v-model:value="form.color" :modes="['hex']" style="width: 120px" />
          <NButton type="primary" :loading="creating" @click="createTag">创建标签</NButton>
        </NSpace>
        <NSpace>
          <NInput v-model:value="groupForm.name" placeholder="新分组名" style="width: 180px" />
          <NButton @click="createGroup">创建分组</NButton>
          <NTag v-for="g in groups" :key="g.id" size="small" :bordered="false">{{ g.name }}</NTag>
        </NSpace>
        <NDataTable :columns="columns" :data="tags" :loading="loading" :bordered="false" size="small" />
      </NSpace>
    </NCard>
  </div>
</template>
