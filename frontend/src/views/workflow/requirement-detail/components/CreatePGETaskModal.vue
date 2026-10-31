<!-- 创建Agent任务对话框 -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import {
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NScrollbar,
  NSelect,
  NSpace,
  NSpin,
  NTooltip
} from 'naive-ui';
import { SUPERPOWER_SKILLS, TaskFramework } from '@/constants/superpowerSkills';
import { createPGETask, previewPGETaskPrompt } from '@/service/api/task';

interface Props {
  show: boolean;
  requirementId: string;
  requirementTitle: string;
}

interface Emits {
  (e: 'update:show', value: boolean): void;
  (e: 'success'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const showModal = computed({
  get: () => props.show,
  set: value => emit('update:show', value)
});

// 默认提示词模板
const PROMPT_TEMPLATES = [
  {
    label: '自定义',
    value: 'custom',
    template: ''
  },
  {
    label: '功能开发',
    value: 'feature',
    template: `请按照以下步骤完成功能开发：

1. **需求分析**：理解并分析功能需求
2. **技术方案设计**：设计合理的技术方案和架构
3. **编码实现**：编写高质量、可维护的代码
4. **测试验证**：确保功能正确性和稳定性
5. **文档更新**：更新相关文档和注释

**技术要求**：
- 遵循项目代码规范
- 确保代码可测试性
- 添加必要的错误处理
- 考虑性能和安全性`
  },
  {
    label: 'Bug修复',
    value: 'bugfix',
    template: `请按照以下步骤完成Bug修复：

1. **问题定位**：准确找到Bug的根因
2. **影响分析**：评估Bug的影响范围
3. **修复方案**：制定最小化影响的修复方案
4. **代码修改**：实施修复并避免引入新问题
5. **回归测试**：验证修复有效且无副作用

**修复要求**：
- 保持代码一致性
- 添加复现步骤说明
- 更新相关测试用例
- 记录问题和解决方案`
  },
  {
    label: '代码重构',
    value: 'refactor',
    template: `请按照以下步骤完成代码重构：

1. **代码审查**：识别需要改进的代码
2. **重构目标**：明确重构的目的和范围
3. **方案设计**：设计更优的代码结构
4. **逐步重构**：小步迭代，保持功能不变
5. **测试验证**：确保重构后功能完全一致

**重构原则**：
- 遵循SOLID原则
- 提高代码可读性
- 降低复杂度和耦合度
- 优化性能和可维护性`
  },
  {
    label: '性能优化',
    value: 'performance',
    template: `请按照以下步骤完成性能优化：

1. **性能分析**：识别性能瓶颈
2. **基准测试**：建立性能基准数据
3. **优化方案**：制定针对性的优化策略
4. **实施优化**：应用优化技术
5. **效果验证**：对比优化前后的性能指标

**优化方向**：
- 减少不必要的计算和渲染
- 优化数据查询和缓存
- 改进算法和数据结构
- 优化资源加载和利用`
  }
];

// 表单数据
const formData = ref({
  description: '',
  framework: TaskFramework.PGE,
  required_skills: [] as string[]
});

// 选中的模板
const selectedTemplate = ref('custom');

// 表单引用
const formRef = ref();

// 加载状态
const loading = ref(false);

// 预览状态
const showPreview = ref(false);
const previewLoading = ref(false);
const previewPrompt = ref('');

// 表单验证规则
const rules = {
  description: {
    required: false,
    message: '请输入任务描述',
    trigger: ['blur', 'input']
  }
};

// 获取类别图标
function getCategoryIcon(category: string): string {
  const iconMap: Record<string, string> = {
    规划类: '📋',
    执行类: '🔨',
    审查类: '🔍',
    设计类: '🎨'
  };
  return iconMap[category] || '📌';
}

// 估算token数量（基于中英文混合文本）
const estimatedTokens = computed(() => {
  const text = previewPrompt.value;
  if (!text) return 0;

  let tokenCount = 0;
  for (let i = 0; i < text.length; i += 1) {
    const charCode = text.charCodeAt(i);
    if (charCode > 255) {
      tokenCount += 1.5;
    } else {
      tokenCount += 0.25;
    }
  }
  return Math.ceil(tokenCount);
});

// 从后端获取提示词预览
async function fetchPromptPreview() {
  if (!showPreview.value) return;

  try {
    previewLoading.value = true;
    const response = await previewPGETaskPrompt({
      requirement_title: props.requirementTitle,
      requirement_id: props.requirementId,
      description: formData.value.description || undefined,
      required_skills: formData.value.required_skills
    });

    if (response.data && response.data.prompt) {
      previewPrompt.value = response.data.prompt;
    }
  } catch (error: any) {
    console.error('获取提示词预览失败:', error);
    window.$message?.error(error.message || '获取预览失败');
  } finally {
    previewLoading.value = false;
  }
}

// 监听表单变化，自动更新预览
watch(
  () => [formData.value.description, formData.value.required_skills, showPreview.value],
  () => {
    if (showPreview.value) {
      fetchPromptPreview();
    }
  },
  { deep: true }
);

// 切换预览
function togglePreview() {
  showPreview.value = !showPreview.value;
  if (showPreview.value) {
    fetchPromptPreview();
  }
}

// 选择模板
function handleTemplateChange(value: string) {
  selectedTemplate.value = value;
  const template = PROMPT_TEMPLATES.find(t => t.value === value);
  if (template && template.template) {
    formData.value.description = template.template;
  } else {
    formData.value.description = '';
  }
}

// 提交表单
async function handleSubmit() {
  try {
    // 验证表单
    await formRef.value?.validate();

    loading.value = true;

    // 调用 API 创建任务，使用需求标题作为任务标题
    await createPGETask({
      requirement_id: props.requirementId,
      title: props.requirementTitle,
      description: formData.value.description || undefined,
      framework: formData.value.framework,
      required_skills: formData.value.required_skills
    });

    // 重置表单
    formData.value = {
      description: '',
      framework: TaskFramework.PGE,
      required_skills: []
    };
    selectedTemplate.value = 'custom';

    // 关闭对话框
    showModal.value = false;

    // 通知父组件
    emit('success');

    window.$message?.success('PGE 任务创建成功');
  } catch (error: any) {
    console.error('创建 PGE 任务失败:', error);
    window.$message?.error(error.message || '创建失败，请重试');
  } finally {
    loading.value = false;
  }
}

// 关闭对话框
function handleClose() {
  showModal.value = false;
}
</script>

<template>
  <NModal
    v-model:show="showModal"
    :mask-closable="false"
    preset="card"
    title="创建Agent任务"
    class="create-pge-task-modal"
    :style="{ width: showPreview ? '1200px' : '700px', maxWidth: '95vw' }"
    @after-leave="handleClose"
  >
    <NSpin :show="loading">
      <div class="modal-content-wrapper" :class="{ 'two-columns': showPreview }">
        <!-- 左侧：表单 -->
        <div class="form-section">
          <NForm ref="formRef" :model="formData" :rules="rules" label-placement="top">
            <!-- 任务描述 -->
            <NFormItem>
              <template #label>
                <div class="form-label-with-action">
                  <span>任务描述</span>
                  <NSelect
                    v-model:value="selectedTemplate"
                    :options="PROMPT_TEMPLATES"
                    size="small"
                    style="width: 120px"
                    @update:value="handleTemplateChange"
                  />
                </div>
              </template>
              <NInput
                v-model:value="formData.description"
                type="textarea"
                placeholder="请选择模板或自定义输入任务描述"
                :rows="8"
              />
            </NFormItem>

            <!-- 任务框架 -->
            <NFormItem label="任务框架">
              <div class="framework-container">
                <div class="framework-badge">
                  <span class="framework-title">PGE</span>
                  <span class="framework-desc">Plan-Generation-Evaluation</span>
                </div>
                <span class="framework-hint">当前仅支持此框架</span>
              </div>
            </NFormItem>

            <!-- Superpower Skills -->
            <NFormItem label="必需技能">
              <NScrollbar style="max-height: 300px">
                <div class="skills-table">
                  <div v-for="(skills, category) in SUPERPOWER_SKILLS" :key="category" class="skill-row">
                    <!-- 第一列：类型名 -->
                    <div class="skill-category-cell">
                      <span class="category-icon">{{ getCategoryIcon(category) }}</span>
                      <span class="category-name">{{ category }}</span>
                    </div>

                    <!-- 第二列：多选项 -->
                    <div class="skill-options-cell">
                      <NCheckboxGroup v-model:value="formData.required_skills">
                        <NSpace :size="8">
                          <NCheckbox v-for="skill in skills" :key="skill.id" :value="skill.id" class="skill-checkbox">
                            <span class="skill-name">{{ skill.name }}</span>
                            <NTooltip trigger="hover">
                              <template #trigger>
                                <span class="skill-help-icon">ℹ️</span>
                              </template>
                              <div class="skill-tooltip-content">
                                <div class="mb-1 font-bold">{{ skill.name }}</div>
                                <div class="text-sm text-neutral-600">{{ skill.description }}</div>
                              </div>
                            </NTooltip>
                          </NCheckbox>
                        </NSpace>
                      </NCheckboxGroup>
                    </div>
                  </div>
                </div>
              </NScrollbar>
            </NFormItem>
          </NForm>

          <!-- 预览切换链接 -->
          <div class="preview-toggle">
            <a class="preview-link" @click="togglePreview">
              {{ showPreview ? '隐藏提示词预览' : '查看提示词预览' }}
            </a>
          </div>
        </div>

        <!-- 右侧：预览 -->
        <div v-if="showPreview" class="preview-section">
          <div class="preview-header">
            <span class="preview-title">任务执行提示词预览</span>
            <span class="preview-token-count">约 {{ estimatedTokens.toLocaleString() }} tokens</span>
          </div>
          <NScrollbar style="max-height: 500px">
            <div class="preview-content">
              <pre v-if="!previewLoading" class="preview-text">{{ previewPrompt }}</pre>
              <NSpin v-else :show="previewLoading" size="small" />
            </div>
          </NScrollbar>
        </div>
      </div>
    </NSpin>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="handleClose">取消</NButton>
        <NButton type="primary" :loading="loading" @click="handleSubmit">创建任务</NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped>
/* Modal 宽度已通过 :style 属性设置 */

/* 内容包装器 - 支持左右两栏布局 */
.modal-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.modal-content-wrapper.two-columns {
  display: flex;
  flex-direction: row;
  gap: 24px;
}

/* 左侧：表单区域 */
.form-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* 右侧：预览区域 */
.preview-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-left: 1px solid var(--color-border-subtle);
  padding-left: 24px;
}

/* 预览头部 */
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border-subtle);
  margin-bottom: 16px;
}

.preview-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.preview-token-count {
  font-size: 12px;
  color: var(--color-text-secondary);
  background-color: #f3f4f6;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 500;
}

/* 预览内容 */
.preview-content {
  flex: 1;
}

.preview-text {
  margin: 0;
  padding: 16px;
  background-color: #f9fafb;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

/* 预览切换链接 */
.preview-toggle {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-subtle);
}

.preview-link {
  color: var(--color-primary);
  text-decoration: underline;
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s;
}

.preview-link:hover {
  color: var(--color-primary-hover);
  text-decoration: underline;
}

/* 表单标签+操作样式 */
.form-label-with-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}

/* 任务框架显示 */
.framework-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.framework-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.framework-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  letter-spacing: 0.5px;
}

.framework-desc {
  font-size: 13px;
  color: #64748b;
}

.framework-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-left: 4px;
}

/* 技能表格样式 */
.skills-table {
  display: flex;
  flex-direction: column;
  gap: 0;
  border: 1px solid var(--color-border-subtle);
  border-radius: 6px;
  overflow: hidden;
}

.skill-row {
  display: flex;
  border-bottom: 1px solid var(--color-border-subtle);
}

.skill-row:last-child {
  border-bottom: none;
}

.skill-row:hover {
  background-color: #f9fafb;
}

/* 第一列：类型名 */
.skill-category-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  min-width: 140px;
  background-color: #f9fafb;
  border-right: 1px solid var(--color-border-subtle);
  font-weight: 500;
}

.category-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.category-name {
  font-size: 14px;
  color: #374151;
}

/* 第二列：多选项 */
.skill-options-cell {
  flex: 1;
  padding: 12px 16px;
  background-color: #ffffff;
}

.skill-checkbox {
  display: inline-flex;
  align-items: center;
}

.skill-name {
  font-size: 13px;
  color: #4b5563;
  margin-right: 4px;
}

.skill-help-icon {
  margin-left: 4px;
  font-size: 14px;
  color: var(--color-text-tertiary);
  cursor: help;
  flex-shrink: 0;
}

.skill-help-icon:hover {
  color: var(--color-text-secondary);
}

.skill-tooltip-content {
  max-width: 300px;
  line-height: 1.5;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .modal-content-wrapper.two-columns {
    flex-direction: column;
  }

  .preview-section {
    border-left: none;
    border-top: 1px solid var(--color-border-subtle);
    padding-left: 0;
    padding-top: 24px;
  }
}
</style>
