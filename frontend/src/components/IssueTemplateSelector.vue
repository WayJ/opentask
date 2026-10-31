<script setup lang="ts">
import { ref } from 'vue';
import { NButton, NCard, NEmpty, NGrid, NGridItem, NSpace, NText } from 'naive-ui';
import { ISSUE_TEMPLATES, type IssueTemplate } from '@/constants/issueTemplates';

interface Props {
  visible: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  select: [template: IssueTemplate];
  close: [];
}>();

// 当前悬停的模板
const hoveredTemplate = ref<string | null>(null);

// 选择模板
function selectTemplate(template: IssueTemplate) {
  emit('select', template);
  emit('close');
}

// 关闭选择器
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
          <NText depth="3">选择一个模板来快速创建规范的 Issue</NText>
        </div>

        <div v-if="ISSUE_TEMPLATES.length === 0" class="template-empty">
          <NEmpty description="暂无可用模板" size="large" />
        </div>

        <NGrid v-else :x-gap="16" :y-gap="16" :cols="3" responsive="screen">
          <NGridItem
            v-for="template in ISSUE_TEMPLATES"
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
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.template-selector-card {
  width: 100%;
  max-width: 900px;
  max-height: 80vh;
  overflow-y: auto;
}

.template-description {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.template-empty {
  padding: 40px 0;
}

.template-item {
  cursor: pointer;
  transition: all 0.2s;
}

.template-item-hovered {
  transform: translateY(-2px);
}

.template-card {
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fff;
  transition: all 0.2s;
  height: 100%;
  display: flex;
  gap: 12px;
}

.template-item:hover .template-card,
.template-item-hovered .template-card {
  border-color: #646cff;
  box-shadow: 0 4px 12px rgba(100, 108, 255, 0.15);
}

.template-icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  border-radius: 8px;
  font-size: 24px;
}

.template-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.template-name {
  font-size: 16px;
}

.template-desc {
  font-size: 12px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.template-footer {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style>
