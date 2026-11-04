<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { NButton, NPopconfirm, NSpace, NTag, NText } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import {
  createProjectMilestone,
  createRepoConfig,
  deleteProjectMilestone,
  deleteRepoConfig,
  fetchProjectHealth,
  fetchProjectMilestones,
  fetchProjectRepos,
  fetchProjectTimeline,
  fetchProjectWatchers,
  postProjectHealth,
  unwatchProject,
  updateProjectMilestone,
  updateRepoConfig,
  watchProject
} from '@/service/api';
import { useAuthStore } from '@/store/modules/auth';
import { useProjectStore } from '@/store/modules/project';
import {
  HEALTH_LABELS,
  HEALTH_TAG_TYPE,
  type HealthStatus,
  type TimelineZoom,
  computeTimelineRange,
  isTimelineEmpty,
  offsetDays,
  timelineDayWidth
} from '@/utils/project-timeline';

defineOptions({
  name: 'ProjectDetail'
});

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();

const project = ref<Api.Project.Project | null>(null);
const repos = ref<Api.Project.RepoConfig[]>([]);
const milestones = ref<Api.Project.Milestone[]>([]);
const loading = ref(false);
const repoLoading = ref(false);
const milestoneLoading = ref(false);

const showRepoModal = ref(false);
const repoModalMode = ref<'create' | 'edit'>('create');
const currentRepo = ref<Api.Project.RepoConfig | null>(null);

const showProjectEditModal = ref(false);
const projectFormData = reactive({
  name: '',
  description: '',
  starts_at: null as string | null,
  target_date: null as string | null
});

const showMilestoneModal = ref(false);
const milestoneModalMode = ref<'create' | 'edit'>('create');
const currentMilestone = ref<Api.Project.Milestone | null>(null);
const milestoneFormData = reactive({
  name: '',
  description: '',
  target_date: null as string | null,
  status: 'planned' as string
});

const repoFormData = reactive({
  name: '',
  url: '',
  main_branch: 'main'
});

const authStore = useAuthStore();
const currentUserId = computed(() => authStore.userInfo?.userId || '');

const healthHistory = ref<Api.Project.HealthUpdate[]>([]);
const healthLoading = ref(false);
const showHealthModal = ref(false);
const healthForm = reactive({
  status: 'on_track' as string,
  note: ''
});
const watching = ref(false);
const watchLoading = ref(false);

const timelineZoom = ref<TimelineZoom>('week');
const timelineData = ref<Api.Project.TimelineData | null>(null);
const timelineLoading = ref(false);

const projectId = (route.query.id as string) || '';

const healthStatusOptions = [
  { label: HEALTH_LABELS.on_track, value: 'on_track' },
  { label: HEALTH_LABELS.at_risk, value: 'at_risk' },
  { label: HEALTH_LABELS.off_track, value: 'off_track' }
];

const healthBadgeType = computed(() => {
  const s = project.value?.health_status as HealthStatus | undefined;
  if (!s || !(s in HEALTH_TAG_TYPE)) return 'default' as const;
  return HEALTH_TAG_TYPE[s as HealthStatus];
});

const healthBadgeLabel = computed(() => {
  const s = project.value?.health_status as HealthStatus | undefined;
  if (!s) return '未设置健康状态';
  return HEALTH_LABELS[s as HealthStatus] || s;
});

const timelineEmpty = computed(() => {
  if (!timelineData.value) return true;
  return isTimelineEmpty(timelineData.value.project, timelineData.value.milestones, timelineData.value.issues);
});

const timelineRange = computed(() => {
  if (!timelineData.value) return null;
  return computeTimelineRange(timelineData.value.project, {
    milestones: timelineData.value.milestones,
    issues: timelineData.value.issues
  });
});

const dayW = computed(() => timelineDayWidth(timelineZoom.value));

const timelineWidth = computed(() => {
  const range = timelineRange.value;
  if (!range) return 600;
  return Math.max(600, (offsetDays(range.start, range.end) + 1) * dayW.value);
});

function leftFor(dateStr: string | null | undefined): number {
  const range = timelineRange.value;
  if (!range || !dateStr) return 0;
  const d = new Date(dateStr);
  return offsetDays(range.start, d) * dayW.value;
}

function barStyle(start: string | null | undefined, end: string | null | undefined) {
  const range = timelineRange.value;
  if (!range) return { left: '0px', width: '0px' };
  const s = start ? new Date(start) : range.start;
  const e = end ? new Date(end) : range.end;
  const left = offsetDays(range.start, s) * dayW.value;
  const width = Math.max(dayW.value, (offsetDays(s, e) + 1) * dayW.value);
  return { left: `${left}px`, width: `${width}px` };
}

function toDateInput(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.slice(0, 10);
}

function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  return value.slice(0, 10);
}

async function loadProject() {
  loading.value = true;
  try {
    const data = await projectStore.getProject(projectId);
    project.value = data;
  } catch {
    window.$message?.error('加载项目详情失败');
  } finally {
    loading.value = false;
  }
}

async function loadRepos() {
  repoLoading.value = true;
  try {
    const response = await fetchProjectRepos(projectId);
    repos.value = response.data || [];
  } catch {
    window.$message?.error('加载仓库配置失败');
  } finally {
    repoLoading.value = false;
  }
}

async function loadMilestones() {
  milestoneLoading.value = true;
  try {
    const response = await fetchProjectMilestones(projectId);
    milestones.value = response.data || [];
  } catch {
    window.$message?.error('加载里程碑失败');
  } finally {
    milestoneLoading.value = false;
  }
}

async function loadHealth() {
  healthLoading.value = true;
  try {
    const response = await fetchProjectHealth(projectId, true);
    healthHistory.value = response.data?.history || [];
  } catch {
    healthHistory.value = [];
  } finally {
    healthLoading.value = false;
  }
}

async function loadWatchers() {
  try {
    const response = await fetchProjectWatchers(projectId);
    const rows = response.data || [];
    watching.value = rows.some(r => r.user_id === currentUserId.value);
  } catch {
    watching.value = false;
  }
}

async function loadTimeline() {
  timelineLoading.value = true;
  try {
    const response = await fetchProjectTimeline(projectId);
    timelineData.value = response.data || null;
  } catch {
    timelineData.value = null;
    window.$message?.error('加载 Timeline 失败');
  } finally {
    timelineLoading.value = false;
  }
}

function openHealthModal() {
  healthForm.status = project.value?.health_status || 'on_track';
  healthForm.note = project.value?.health_note || '';
  showHealthModal.value = true;
}

async function handlePostHealth() {
  try {
    await postProjectHealth(projectId, {
      status: healthForm.status,
      note: healthForm.note || null
    });
    showHealthModal.value = false;
    await loadProject();
    await loadHealth();
    window.$message?.success('健康状态已更新');
  } catch {
    window.$message?.error('更新健康状态失败');
  }
}

async function toggleWatch() {
  watchLoading.value = true;
  try {
    if (watching.value) {
      await unwatchProject(projectId);
      watching.value = false;
      window.$message?.success('已取消关注');
    } else {
      await watchProject(projectId);
      watching.value = true;
      window.$message?.success('已关注项目');
    }
  } catch {
    window.$message?.error('操作失败');
  } finally {
    watchLoading.value = false;
  }
}

function goBack() {
  router.push('/workflow/projects');
}

function openEditProjectModal() {
  if (project.value) {
    projectFormData.name = project.value.name;
    projectFormData.description = project.value.description || '';
    projectFormData.starts_at = toDateInput(project.value.starts_at);
    projectFormData.target_date = toDateInput(project.value.target_date);
    showProjectEditModal.value = true;
  }
}

async function handleUpdateProject() {
  if (!project.value) return;
  try {
    await projectStore.editProject(project.value.id, {
      name: projectFormData.name,
      description: projectFormData.description,
      starts_at: projectFormData.starts_at || null,
      target_date: projectFormData.target_date || null
    });
    showProjectEditModal.value = false;
    await loadProject();
    window.$message?.success('项目更新成功');
  } catch {
    window.$message?.error('项目更新失败');
  }
}

function openCreateRepoModal() {
  repoModalMode.value = 'create';
  resetRepoForm();
  showRepoModal.value = true;
}

function openEditRepoModal(repo: Api.Project.RepoConfig) {
  repoModalMode.value = 'edit';
  currentRepo.value = repo;
  repoFormData.name = repo.name;
  repoFormData.url = repo.url;
  repoFormData.main_branch = repo.main_branch;
  showRepoModal.value = true;
}

function resetRepoForm() {
  repoFormData.name = '';
  repoFormData.url = '';
  repoFormData.main_branch = 'main';
  currentRepo.value = null;
}

async function handleCreateRepo() {
  try {
    const data = {
      ...repoFormData,
      project_id: projectId
    };
    await createRepoConfig(projectId, data);
    showRepoModal.value = false;
    resetRepoForm();
    await loadRepos();
    window.$message?.success('仓库配置创建成功');
  } catch {
    window.$message?.error('仓库配置创建失败');
  }
}

async function handleUpdateRepo() {
  if (!currentRepo.value) return;
  try {
    await updateRepoConfig(projectId, currentRepo.value.id, repoFormData);
    showRepoModal.value = false;
    resetRepoForm();
    await loadRepos();
    window.$message?.success('仓库配置更新成功');
  } catch {
    window.$message?.error('仓库配置更新失败');
  }
}

async function handleDeleteRepo(repo: Api.Project.RepoConfig) {
  try {
    await deleteRepoConfig(projectId, repo.id);
    await loadRepos();
    window.$message?.success('仓库配置删除成功');
  } catch {
    window.$message?.error('仓库配置删除失败');
  }
}

function resetMilestoneForm() {
  milestoneFormData.name = '';
  milestoneFormData.description = '';
  milestoneFormData.target_date = null;
  milestoneFormData.status = 'planned';
  currentMilestone.value = null;
}

function openCreateMilestoneModal() {
  milestoneModalMode.value = 'create';
  resetMilestoneForm();
  showMilestoneModal.value = true;
}

function openEditMilestoneModal(m: Api.Project.Milestone) {
  milestoneModalMode.value = 'edit';
  currentMilestone.value = m;
  milestoneFormData.name = m.name;
  milestoneFormData.description = m.description || '';
  milestoneFormData.target_date = toDateInput(m.target_date);
  milestoneFormData.status = m.status || 'planned';
  showMilestoneModal.value = true;
}

async function handleCreateMilestone() {
  try {
    await createProjectMilestone(projectId, {
      name: milestoneFormData.name,
      description: milestoneFormData.description || null,
      target_date: milestoneFormData.target_date || null,
      status: milestoneFormData.status
    });
    showMilestoneModal.value = false;
    resetMilestoneForm();
    await loadMilestones();
    window.$message?.success('里程碑创建成功');
  } catch {
    window.$message?.error('里程碑创建失败');
  }
}

async function handleUpdateMilestone() {
  if (!currentMilestone.value) return;
  try {
    await updateProjectMilestone(projectId, currentMilestone.value.id, {
      name: milestoneFormData.name,
      description: milestoneFormData.description || null,
      target_date: milestoneFormData.target_date || null,
      status: milestoneFormData.status
    });
    showMilestoneModal.value = false;
    resetMilestoneForm();
    await loadMilestones();
    window.$message?.success('里程碑更新成功');
  } catch {
    window.$message?.error('里程碑更新失败');
  }
}

async function handleDeleteMilestone(m: Api.Project.Milestone) {
  try {
    await deleteProjectMilestone(projectId, m.id);
    await loadMilestones();
    window.$message?.success('里程碑删除成功');
  } catch {
    window.$message?.error('里程碑删除失败');
  }
}

const milestoneStatusLabel: Record<string, string> = {
  planned: '计划中',
  done: '已完成'
};

const milestoneStatusOptions = [
  { label: '计划中', value: 'planned' },
  { label: '已完成', value: 'done' }
];

const repoColumns: DataTableColumns<Api.Project.RepoConfig> = [
  {
    title: '仓库名称',
    key: 'name',
    width: 200,
    ellipsis: { tooltip: true }
  },
  {
    title: '仓库地址',
    key: 'url',
    width: 400,
    ellipsis: { tooltip: true }
  },
  {
    title: '主分支',
    key: 'main_branch',
    width: 120
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    fixed: 'right' as const,
    render: row =>
      h(NSpace, null, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => openEditRepoModal(row) }, { default: () => '编辑' }),
          h(
            NPopconfirm,
            {
              onPositiveClick: () => handleDeleteRepo(row)
            },
            {
              trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
              default: () => '确定删除此仓库配置吗?'
            }
          )
        ]
      })
  }
];

const milestoneColumns: DataTableColumns<Api.Project.Milestone> = [
  {
    title: '名称',
    key: 'name',
    width: 200,
    ellipsis: { tooltip: true }
  },
  {
    title: '目标日期',
    key: 'target_date',
    width: 140,
    render: row => formatDate(row.target_date)
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    render: row =>
      h(
        NTag,
        { size: 'small', type: row.status === 'done' ? 'success' : 'default' },
        { default: () => milestoneStatusLabel[row.status] || row.status }
      )
  },
  {
    title: '描述',
    key: 'description',
    ellipsis: { tooltip: true },
    render: row => row.description || '—'
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    fixed: 'right' as const,
    render: row =>
      h(NSpace, null, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => openEditMilestoneModal(row) }, { default: () => '编辑' }),
          h(
            NPopconfirm,
            {
              onPositiveClick: () => handleDeleteMilestone(row)
            },
            {
              trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
              default: () => '确定删除此里程碑吗?'
            }
          )
        ]
      })
  }
];

onMounted(() => {
  loadProject();
  loadRepos();
  loadMilestones();
  loadHealth();
  loadWatchers();
  loadTimeline();
});
</script>

<template>
  <div class="project-detail-container">
    <NSpin :show="loading">
      <template v-if="project">
        <!-- Header -->
        <NCard :bordered="false">
          <NSpace align="center" justify="space-between" style="width: 100%">
            <NSpace align="center">
              <NButton text @click="goBack">
                <template #icon>
                  <icon-mdi-arrow-left />
                </template>
                返回
              </NButton>
              <NText strong style="font-size: 20px">{{ project.name }}</NText>
              <NTag v-if="project.is_active" type="success" size="small">活跃</NTag>
              <NTag v-else type="default" size="small">已归档</NTag>
              <NTag :type="healthBadgeType" size="small">{{ healthBadgeLabel }}</NTag>
              <NText v-if="project.health_note" depth="3" style="max-width: 280px" class="truncate">
                {{ project.health_note }}
              </NText>
            </NSpace>
            <NSpace>
              <NButton :loading="watchLoading" @click="toggleWatch">
                {{ watching ? '取消关注' : '关注' }}
              </NButton>
              <NButton @click="openHealthModal">更新健康</NButton>
              <NButton @click="openEditProjectModal">
                <template #icon>
                  <icon-mdi-pencil />
                </template>
                编辑
              </NButton>
            </NSpace>
          </NSpace>
        </NCard>

        <!-- Description -->
        <NCard title="项目描述" :bordered="false" class="mt-4">
          <NText v-if="project.description">{{ project.description }}</NText>
          <NText v-else depth="3">暂无描述</NText>
        </NCard>

        <NCard title="健康历史" :bordered="false" class="mt-4">
          <NSpin :show="healthLoading">
            <NEmpty v-if="!healthLoading && healthHistory.length === 0" description="暂无健康更新" size="small" />
            <NTimeline v-else>
              <NTimelineItem
                v-for="row in healthHistory"
                :key="row.id"
                :type="(HEALTH_TAG_TYPE[row.status as HealthStatus] as any) || 'default'"
                :title="HEALTH_LABELS[row.status as HealthStatus] || row.status"
                :time="row.created_at ? new Date(row.created_at).toLocaleString() : ''"
              >
                {{ row.note || '—' }}
              </NTimelineItem>
            </NTimeline>
          </NSpin>
        </NCard>

        <!-- Milestones (E8-S1) -->
        <NCard :bordered="false" class="mt-4">
          <template #header>
            <NSpace align="center" justify="space-between" style="width: 100%">
              <NText strong>里程碑</NText>
              <NButton type="primary" size="small" @click="openCreateMilestoneModal">
                <template #icon>
                  <icon-mdi-plus />
                </template>
                添加里程碑
              </NButton>
            </NSpace>
          </template>
          <NSpin :show="milestoneLoading">
            <NEmpty v-if="!milestoneLoading && milestones.length === 0" description="暂无里程碑" size="small" />
            <NDataTable
              v-else
              :columns="milestoneColumns"
              :data="milestones"
              :row-key="(row: Api.Project.Milestone) => row.id"
              :scroll-x="900"
              striped
              size="small"
            />
          </NSpin>
        </NCard>

        <!-- Repositories -->
        <NCard :bordered="false" class="mt-4">
          <template #header>
            <NSpace align="center" justify="space-between" style="width: 100%">
              <NText strong>仓库配置</NText>
              <NButton type="primary" size="small" @click="openCreateRepoModal">
                <template #icon>
                  <icon-mdi-plus />
                </template>
                添加仓库
              </NButton>
            </NSpace>
          </template>
          <NSpin :show="repoLoading">
            <NEmpty v-if="!repoLoading && repos.length === 0" description="暂无仓库配置" size="small" />
            <NDataTable
              v-else
              :columns="repoColumns"
              :data="repos"
              :row-key="(row: Api.Project.RepoConfig) => row.id"
              :scroll-x="900"
              striped
              size="small"
            />
          </NSpin>
        </NCard>

        <!-- Timeline (E8-S2) -->
        <NCard :bordered="false" class="mt-4">
          <template #header>
            <NSpace align="center" justify="space-between" style="width: 100%">
              <NText strong>Timeline</NText>
              <NRadioGroup v-model:value="timelineZoom" size="small">
                <NRadioButton value="week">周</NRadioButton>
                <NRadioButton value="month">月</NRadioButton>
              </NRadioGroup>
            </NSpace>
          </template>
          <NSpin :show="timelineLoading">
            <div v-if="timelineEmpty" class="py-24px">
              <NEmpty description="设置项目日期或添加里程碑后即可查看 Timeline">
                <template #extra>
                  <NSpace>
                    <NButton size="small" @click="openEditProjectModal">设置项目日期</NButton>
                    <NButton size="small" type="primary" @click="openCreateMilestoneModal">添加里程碑</NButton>
                  </NSpace>
                </template>
              </NEmpty>
            </div>
            <div v-else class="timeline-scroll">
              <div class="timeline-canvas" :style="{ width: timelineWidth + 'px' }">
                <div v-if="timelineData?.project" class="timeline-row">
                  <div class="timeline-label">项目</div>
                  <div class="timeline-track">
                    <div
                      class="timeline-bar project-bar"
                      :style="barStyle(timelineData.project.starts_at, timelineData.project.target_date)"
                    >
                      {{ timelineData.project.name }}
                    </div>
                  </div>
                </div>
                <div v-for="m in timelineData?.milestones || []" :key="m.id" class="timeline-row">
                  <div class="timeline-label">{{ m.name }}</div>
                  <div class="timeline-track">
                    <div
                      v-if="m.target_date"
                      class="timeline-diamond"
                      :style="{ left: leftFor(m.target_date) + 'px' }"
                      :title="m.name"
                    />
                    <NText v-else depth="3" style="font-size: 12px">无目标日期</NText>
                  </div>
                </div>
                <div v-for="issue in timelineData?.issues || []" :key="issue.id" class="timeline-row">
                  <div class="timeline-label">{{ issue.issue_code || issue.title }}</div>
                  <div class="timeline-track">
                    <div
                      class="timeline-dot"
                      :style="{ left: leftFor(issue.due_date) + 'px' }"
                      :title="issue.title"
                    />
                  </div>
                </div>
              </div>
            </div>
          </NSpin>
        </NCard>

        <!-- Meta Info -->
        <NCard title="项目信息" :bordered="false" class="mt-4">
          <NDescriptions :column="1" bordered label-placement="left" label-style="width: 120px">
            <NDescriptionsItem label="项目ID">
              <NText code>{{ project.id }}</NText>
            </NDescriptionsItem>
            <NDescriptionsItem label="开始日期">
              {{ formatDate(project.starts_at) }}
            </NDescriptionsItem>
            <NDescriptionsItem label="目标日期">
              {{ formatDate(project.target_date) }}
            </NDescriptionsItem>
            <NDescriptionsItem label="创建时间">
              {{ new Date(project.created_at).toLocaleString() }}
            </NDescriptionsItem>
            <NDescriptionsItem label="更新时间">
              {{ new Date(project.updated_at).toLocaleString() }}
            </NDescriptionsItem>
          </NDescriptions>
        </NCard>
      </template>

      <NEmpty v-else-if="!loading" description="项目不存在" size="large">
        <template #extra>
          <NButton @click="goBack">返回列表</NButton>
        </template>
      </NEmpty>
    </NSpin>

    <!-- Create/Edit Repo Modal -->
    <NModal
      v-model:show="showRepoModal"
      preset="card"
      :title="repoModalMode === 'create' ? '添加仓库配置' : '编辑仓库配置'"
      style="width: 700px"
    >
      <NForm label-placement="left" label-width="100px">
        <NFormItem label="仓库名称" required>
          <NInput v-model:value="repoFormData.name" placeholder="请输入仓库名称" />
        </NFormItem>
        <NFormItem label="仓库地址" required>
          <NInput
            v-model:value="repoFormData.url"
            placeholder="请输入 Git 仓库 URL (例如: https://github.com/user/repo.git)"
          />
        </NFormItem>
        <NFormItem label="主分支">
          <NInput v-model:value="repoFormData.main_branch" placeholder="默认为 main" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showRepoModal = false">取消</NButton>
          <NButton type="primary" @click="repoModalMode === 'create' ? handleCreateRepo() : handleUpdateRepo()">
            {{ repoModalMode === 'create' ? '创建' : '保存' }}
          </NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Edit Project Modal -->
    <NModal v-model:show="showProjectEditModal" preset="card" title="编辑项目" style="width: 600px">
      <NForm label-placement="left" label-width="100px">
        <NFormItem label="项目名称" required>
          <NInput v-model:value="projectFormData.name" placeholder="请输入项目名称" />
        </NFormItem>
        <NFormItem label="项目描述">
          <NInput v-model:value="projectFormData.description" type="textarea" :rows="4" placeholder="请输入项目描述" />
        </NFormItem>
        <NFormItem label="开始日期">
          <NDatePicker
            v-model:formatted-value="projectFormData.starts_at"
            type="date"
            value-format="yyyy-MM-dd"
            clearable
            style="width: 100%"
          />
        </NFormItem>
        <NFormItem label="目标日期">
          <NDatePicker
            v-model:formatted-value="projectFormData.target_date"
            type="date"
            value-format="yyyy-MM-dd"
            clearable
            style="width: 100%"
          />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showProjectEditModal = false">取消</NButton>
          <NButton type="primary" @click="handleUpdateProject">保存</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Create/Edit Milestone Modal -->
    <NModal
      v-model:show="showMilestoneModal"
      preset="card"
      :title="milestoneModalMode === 'create' ? '添加里程碑' : '编辑里程碑'"
      style="width: 600px"
    >
      <NForm label-placement="left" label-width="100px">
        <NFormItem label="名称" required>
          <NInput v-model:value="milestoneFormData.name" placeholder="请输入里程碑名称" />
        </NFormItem>
        <NFormItem label="描述">
          <NInput v-model:value="milestoneFormData.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </NFormItem>
        <NFormItem label="目标日期">
          <NDatePicker
            v-model:formatted-value="milestoneFormData.target_date"
            type="date"
            value-format="yyyy-MM-dd"
            clearable
            style="width: 100%"
          />
        </NFormItem>
        <NFormItem label="状态">
          <NSelect v-model:value="milestoneFormData.status" :options="milestoneStatusOptions" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showMilestoneModal = false">取消</NButton>
          <NButton
            type="primary"
            @click="milestoneModalMode === 'create' ? handleCreateMilestone() : handleUpdateMilestone()"
          >
            {{ milestoneModalMode === 'create' ? '创建' : '保存' }}
          </NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Health Update Modal (E8-S2) -->
    <NModal v-model:show="showHealthModal" preset="card" title="更新项目健康" style="width: 520px">
      <NForm label-placement="left" label-width="100px">
        <NFormItem label="状态" required>
          <NSelect v-model:value="healthForm.status" :options="healthStatusOptions" />
        </NFormItem>
        <NFormItem label="说明">
          <NInput v-model:value="healthForm.note" type="textarea" :rows="3" placeholder="可选说明" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showHealthModal = false">取消</NButton>
          <NButton type="primary" @click="handlePostHealth">保存</NButton>
        </NSpace>
      </template>
    </NModal>

  </div>
</template>

<style scoped>
.project-detail-container {
  padding: 16px;
}

.mt-2 {
  margin-top: 8px;
}

.mt-4 {
  margin-top: 16px;
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-scroll {
  overflow-x: auto;
  padding-bottom: 8px;
}

.timeline-canvas {
  min-height: 120px;
}

.timeline-row {
  display: flex;
  align-items: center;
  min-height: 36px;
  margin-bottom: 8px;
}

.timeline-label {
  width: 140px;
  flex-shrink: 0;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 8px;
}

.timeline-track {
  position: relative;
  flex: 1;
  height: 28px;
  background: rgba(128, 128, 128, 0.08);
  border-radius: 4px;
}

.timeline-bar {
  position: absolute;
  top: 4px;
  height: 20px;
  border-radius: 4px;
  font-size: 11px;
  line-height: 20px;
  padding: 0 8px;
  color: #fff;
  overflow: hidden;
  white-space: nowrap;
}

.project-bar {
  background: #2080f0;
}

.timeline-diamond {
  position: absolute;
  top: 6px;
  width: 14px;
  height: 14px;
  background: #f0a020;
  transform: translateX(-50%) rotate(45deg);
}

.timeline-dot {
  position: absolute;
  top: 8px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #18a058;
  transform: translateX(-50%);
}
</style>
