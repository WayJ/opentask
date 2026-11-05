<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { NButton, NSelect, NSpace, NTag, NText } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import { useProjectStore } from '@/store/modules/project';
import { fetchProjectTemplates, type ProjectTemplateRow } from '@/service/api/project-templates';
import { previewMilestones } from '@/utils/projectTemplate';

defineOptions({
  name: 'Projects'
});

const projectStore = useProjectStore();
const router = useRouter();

const projects = ref<Api.Project.Project[]>([]);
const loading = ref(false);
const showCreateModal = ref(false);
const showEditModal = ref(false);
const currentProject = ref<Api.Project.Project | null>(null);

// Form data
const formData = reactive({
  name: '',
  description: '',
  template_id: null as string | null
});

const templateRows = ref<ProjectTemplateRow[]>([]);
const templateOptions = computed(() =>
  templateRows.value.map(t => ({ label: t.name, value: t.id }))
);
const selectedTemplate = computed(() =>
  templateRows.value.find(t => t.id === formData.template_id) || null
);
const milestonePreview = computed(() => {
  const miles = selectedTemplate.value?.payload?.milestones || [];
  const base = new Date().toISOString().slice(0, 10);
  return previewMilestones(miles as any, base);
});

async function loadTemplates() {
  const { data } = await fetchProjectTemplates();
  templateRows.value = data?.rows || [];
}

function onTemplatePicked(id: string | null) {
  const tpl = templateRows.value.find(t => t.id === id);
  if (tpl?.payload?.description && !formData.description) {
    formData.description = String(tpl.payload.description);
  }
}

// Load projects
async function loadProjects() {
  loading.value = true;
  try {
    await projectStore.getProjects();
    projects.value = projectStore.projects;
  } finally {
    loading.value = false;
  }
}

// Create project
async function handleCreate() {
  try {
    await projectStore.addProject({
      name: formData.name,
      description: formData.description,
      template_id: formData.template_id || undefined
    });
    showCreateModal.value = false;
    resetForm();
    await loadProjects();
    window.$message?.success('项目创建成功');
  } catch {
    window.$message?.error('项目创建失败');
  }
}

// Edit project
async function handleEdit() {
  if (!currentProject.value) return;
  try {
    await projectStore.editProject(currentProject.value.id, {
      name: formData.name,
      description: formData.description
    });
    showEditModal.value = false;
    resetForm();
    await loadProjects();
    window.$message?.success('项目更新成功');
  } catch {
    window.$message?.error('项目更新失败');
  }
}

// Delete project
function handleDelete(project: Api.Project.Project) {
  window.$dialog?.warning({
    title: '确认删除',
    content: `确定要删除项目 "${project.name}" 吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await projectStore.removeProject(project.id);
        await loadProjects();
        window.$message?.success('项目删除成功');
      } catch {
        window.$message?.error('项目删除失败');
      }
    }
  });
}

// Open create modal
function openCreateModal() {
  resetForm();
  showCreateModal.value = true;
}

// Open edit modal
function openEditModal(project: Api.Project.Project) {
  currentProject.value = project;
  formData.name = project.name;
  formData.description = project.description || '';
  showEditModal.value = true;
}

// Reset form
function resetForm() {
  formData.name = '';
  formData.description = '';
  formData.template_id = null;
  currentProject.value = null;
}

// View project details
function viewProject(project: Api.Project.Project) {
  router.push({ path: '/workflow/project-detail', query: { id: project.id } });
}

// Table columns
const columns: DataTableColumns<Api.Project.Project> = [
  {
    title: '项目名称',
    key: 'name',
    width: 200,
    ellipsis: { tooltip: true }
  },
  {
    title: '描述',
    key: 'description',
    width: 300,
    ellipsis: { tooltip: true },
    render: row => row.description || '无描述'
  },
  {
    title: '状态',
    key: 'is_active',
    width: 100,
    render: row =>
      h(
        NTag,
        { type: row.is_active ? 'success' : 'default', size: 'small' },
        { default: () => (row.is_active ? '活跃' : '已归档') }
      )
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render: row =>
      h(NText, { depth: 3, style: { fontSize: '12px' } }, { default: () => new Date(row.created_at).toLocaleString() })
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    fixed: 'right' as const,
    render: row =>
      h(NSpace, null, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => viewProject(row) }, { default: () => '查看详情' }),
          h(NButton, { size: 'small', onClick: () => openEditModal(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row) }, { default: () => '删除' })
        ]
      })
  }
];

onMounted(() => {
  loadProjects();
  loadTemplates();
});
</script>

<template>
  <div class="projects-container">
    <NCard :bordered="false">
      <template #header>
        <NSpace align="center" justify="space-between" style="width: 100%">
          <NText strong style="font-size: 16px">项目管理</NText>
          <NButton type="primary" @click="openCreateModal">
            <template #icon>
              <icon-mdi-plus />
            </template>
            新建项目
          </NButton>
        </NSpace>
      </template>

      <NSpin :show="loading">
        <NEmpty v-if="!loading && projects.length === 0" description="暂无项目" size="large" />
        <NDataTable
          v-else
          :columns="columns"
          :data="projects"
          :row-key="(row: Api.Project.Project) => row.id"
          :scroll-x="1000"
          striped
          size="small"
        />
      </NSpin>
    </NCard>

    <!-- Create Modal -->
    <NModal v-model:show="showCreateModal" preset="card" title="新建项目" style="width: 600px">
      <NForm ref="formRef" :model="formData" label-placement="left" label-width="80">
        <NFormItem label="项目名称" path="name" :rule="{ required: true, message: '请输入项目名称' }">
          <NInput v-model:value="formData.name" placeholder="请输入项目名称" />
        </NFormItem>
        <NFormItem label="项目描述" path="description">
          <NInput
            v-model:value="formData.description"
            type="textarea"
            placeholder="请输入项目描述（可选）"
            :autosize="{ minRows: 3, maxRows: 6 }"
          />
        </NFormItem>
        <NFormItem label="模板" path="template_id">
          <NSelect
            v-model:value="formData.template_id"
            :options="templateOptions"
            clearable
            placeholder="可选：从 Project 模板创建"
            @update:value="onTemplatePicked"
          />
        </NFormItem>
        <div v-if="milestonePreview.length" class="template-preview">
          <NText depth="3">将种子的里程碑（相对今天）：</NText>
          <ul>
            <li v-for="(m, i) in milestonePreview" :key="i">
              {{ m.name }} <span v-if="m.targetDate">— {{ m.targetDate }}</span>
            </li>
          </ul>
        </div>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCreateModal = false">取消</NButton>
          <NButton type="primary" @click="handleCreate">创建</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Edit Modal -->
    <NModal v-model:show="showEditModal" preset="card" title="编辑项目" style="width: 600px">
      <NForm ref="formRef" :model="formData" label-placement="left" label-width="80">
        <NFormItem label="项目名称" path="name" :rule="{ required: true, message: '请输入项目名称' }">
          <NInput v-model:value="formData.name" placeholder="请输入项目名称" />
        </NFormItem>
        <NFormItem label="项目描述" path="description">
          <NInput
            v-model:value="formData.description"
            type="textarea"
            placeholder="请输入项目描述（可选）"
            :autosize="{ minRows: 3, maxRows: 6 }"
          />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showEditModal = false">取消</NButton>
          <NButton type="primary" @click="handleEdit">保存</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.projects-container {
  padding: 16px;
}
</style>
