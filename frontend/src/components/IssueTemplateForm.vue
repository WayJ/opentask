<script setup lang="ts">
import { computed, reactive, watch } from 'vue';
import { NButton, NCard, NFormItem, NInput, NSelect, NSpace, NText } from 'naive-ui';
import { type IssueTemplate, generateTemplateContent } from '@/constants/issueTemplates';
import { $t } from '@/locales';

interface Props {
  visible: boolean;
  template: IssueTemplate | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  submit: [title: string, content: string];
  close: [];
}>();

// 表单数据
const formData = reactive<Record<string, any>>({});

// 重置表单
function resetForm() {
  const keys = Object.keys(formData);
  for (let i = 0; i < keys.length; i += 1) {
    const key = keys[i];
    // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
    delete formData[key];
  }
}

// 监听模板变化
watch(
  () => props.template,
  newTemplate => {
    if (newTemplate) {
      // 初始化表单数据
      newTemplate.fields.forEach(field => {
        if (field.defaultValue !== undefined) {
          formData[field.name] = field.defaultValue;
        } else {
          formData[field.name] = '';
        }
      });
    }
  }
);

// 监听可见性变化
watch(
  () => props.visible,
  visible => {
    if (!visible) {
      resetForm();
    }
  }
);

// 标题字段
const titleField = computed(() => {
  return props.template?.fields.find(f => f.name === 'title');
});

// 其他字段（排除标题）
const otherFields = computed(() => {
  return props.template?.fields.filter(f => f.name !== 'title') || [];
});

// 提交表单
function handleSubmit() {
  if (!props.template) return;

  // 验证必填字段
  const requiredFields = props.template.fields.filter(f => f.required);
  for (const field of requiredFields) {
    if (!formData[field.name] || (typeof formData[field.name] === 'string' && formData[field.name].trim() === '')) {
      window.$message?.error(`请填写${field.label}`);
      return;
    }
  }

  // 生成标题和内容
  const title = formData.title || '';
  const content = generateTemplateContent(props.template, formData);

  emit('submit', title, content);
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible && template" class="template-form-overlay" @click.self="emit('close')">
      <NCard class="template-form-card" :bordered="true">
        <template #header>
          <NSpace align="center">
            <span :class="template.icon" class="template-icon" />
            <NText strong>{{ template.name }}</NText>
          </NSpace>
        </template>

        <template #header-extra>
          <NButton text @click="emit('close')">
            <icon-mdi-close />
          </NButton>
        </template>

        <div class="template-form-content">
          <NText depth="3" style="margin-bottom: 20px; display: block">
            {{ template.description }}
          </NText>

          <div class="form-fields">
            <!-- 标题字段 -->
            <NFormItem v-if="titleField" :label="titleField.label" :required="titleField.required">
              <NInput v-model:value="formData[titleField.name]" :placeholder="titleField.placeholder" size="large" />
            </NFormItem>

            <!-- 其他字段 -->
            <NFormItem v-for="field in otherFields" :key="field.name" :label="field.label" :required="field.required">
              <NInput
                v-if="field.type === 'textarea'"
                v-model:value="formData[field.name]"
                type="textarea"
                :placeholder="field.placeholder"
                :rows="field.name === 'description' ? 8 : 4"
              />
              <NSelect
                v-else-if="field.type === 'select'"
                v-model:value="formData[field.name]"
                :options="field.options?.map(opt => ({ label: opt, value: opt })) || []"
                :placeholder="field.placeholder"
              />
              <NCheckbox v-else-if="field.type === 'checkbox'" v-model:checked="formData[field.name]">
                {{ field.label }}
              </NCheckbox>
              <NInput v-else v-model:value="formData[field.name]" :placeholder="field.placeholder" />
            </NFormItem>

            <!-- 预览区域 -->
            <NFormItem :label="$t('page.issueTemplate.contentPreview')">
              <div class="content-preview">
                <NText depth="3" style="font-size: 12px; margin-bottom: 8px; display: block">
                  {{ $t('page.issueTemplate.previewHint') }}
                </NText>
                <div class="preview-content">
                  <pre>{{ generateTemplateContent(template, formData) }}</pre>
                </div>
              </div>
            </NFormItem>
          </div>
        </div>

        <template #footer>
          <NSpace justify="end">
            <NButton @click="emit('close')">{{ $t('page.issueTemplate.cancel') }}</NButton>
            <NButton type="primary" @click="handleSubmit">{{ $t('page.issueForm.createTitle') }}</NButton>
          </NSpace>
        </template>
      </NCard>
    </div>
  </Teleport>
</template>

<style scoped>
.template-form-overlay {
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

.template-form-card {
  width: 100%;
  max-width: 800px;
  max-height: 85vh;
  overflow-y: auto;
}

.template-icon {
  font-size: 24px;
}

.template-form-content {
  padding: 8px 0;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.content-preview {
  width: 100%;
}

.preview-content {
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 12px;
  max-height: 200px;
  overflow-y: auto;
}

.preview-content pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
