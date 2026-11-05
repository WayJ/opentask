<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { NButton, NCard, NEmpty, NGrid, NGridItem, NSpace, NSpin, NText } from 'naive-ui';
import { ISSUE_TEMPLATES, type IssueTemplate } from '@/constants/issueTemplates';
import { type IssueTemplateRow, fetchIssueTemplates } from '@/service/api/issue-templates';

interface Props {
  visible: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  select: [template: IssueTemplate];
  close: [];
}>();

const hoveredTemplate = ref<string | null>(null);
const loading = ref(false);
const templates = ref<IssueTemplate[]>([...ISSUE_TEMPLATES]);

function mapRow(row: IssueTemplateRow): IssueTemplate {
  const fields =
    row.payload?.fields && row.payload.fields.length > 0
      ? row.payload.fields
      : ISSUE_TEMPLATES.find(t => t.id === row.seedKey)?.fields || [
          {
            name: 'title',
            label: '标题',
            type: 'text',
            required: true,
            placeholder: '标题'
          },
          {
            name: 'description',
            label: '描述',
            type: 'textarea',
            required: false,
            placeholder: row.payload?.description || ''
          }
        ];
  return {
    id: row.id,
    apiId: row.id,
    seedKey: row.seedKey || undefined,
    name: row.name,
    description: row.description || '',
    icon: row.icon || 'i-carbon-document',
    fields,
    defaultType: row.payload?.type,
    defaultPriority: row.payload?.priority
  };
}

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchIssueTemplates();
    if (error || !data?.rows?.length) {
      templates.value = [...ISSUE_TEMPLATES];
      return;
    }
    templates.value = data.rows.map(mapRow);
  } catch {
    templates.value = [...ISSUE_TEMPLATES];
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.visible,
  v => {
    if (v) load();
  }
);

onMounted(() => {
  if (props.visible) load();
});

function selectTemplate(template: IssueTemplate) {
  emit('select', template);
  emit('close');
}

function close() {
  emit('close');
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="template-selector-overlay" @click.self="close">
      <NCard class="template-selector-card" title="选择 Issue 模板" :bordered="true">
        <template #header-extra>
          <NButton text @click="close">
            <icon-mdi-close />
          </NButton>
        </template>

        <div class="template-description">
          <NText depth="3">选择一个模板来快速创建规范的 Issue（工作区模板）</NText>
        </div>

        <NSpin :show="loading">
          <div v-if="!loading && templates.length === 0" class="template-empty">
            <NEmpty description="暂无可用模板" size="large" />
          </div>

          <NGrid v-else :x-gap="16" :y-gap="16" :cols="3" responsive="screen">
            <NGridItem
              v-for="template in templates"
              :key="template.id"
              class="template-item"
              :class="[hoveredTemplate === template.id ? 'template-item-hovered' : '']"
              @click="selectTemplate(template)"
              @mouseenter="hoveredTemplate = template.id"
              @mouseleave="hoveredTemplate = null"
            >
              <div class="template-card">
                <div class="template-icon">
                  <span :class="template.icon" />
                </div>
                <div class="template-content">
                  <NText strong class="template-name">{{ template.name }}</NText>
                  <NText depth="3" class="template-desc">{{ template.description }}</NText>
                </div>
              </div>
            </NGridItem>
          </NGrid>
        </NSpin>

        <div class="template-footer">
          <NSpace justify="space-between">
            <NText depth="3" style="font-size: 12px">提示：你也可以不使用模板，直接创建空白 Issue</NText>
            <NButton text @click="close">
              <NText depth="3">取消</NText>
            </NButton>
          </NSpace>
        </div>
      </NCard>
    </div>
  </Teleport>
</template>

<style scoped>
.template-selector-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  padding: 24px;
}
.template-selector-card {
  width: min(860px, 100%);
  max-height: 80vh;
  overflow: auto;
}
.template-description {
  margin-bottom: 16px;
}
.template-empty {
  padding: 32px 0;
}
.template-item {
  cursor: pointer;
}
.template-card {
  border: 1px solid rgba(128, 128, 128, 0.25);
  border-radius: 8px;
  padding: 16px;
  height: 100%;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.template-item-hovered .template-card {
  border-color: var(--primary-color, #18a058);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.template-icon {
  font-size: 22px;
  margin-bottom: 8px;
}
.template-name {
  display: block;
  margin-bottom: 4px;
}
.template-desc {
  font-size: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.template-footer {
  margin-top: 16px;
}
</style>
