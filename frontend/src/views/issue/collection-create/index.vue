<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { NButton, NCard, NDivider, NForm, NFormItem, NIcon, NInput, NSpace } from 'naive-ui';
import { CollectionStatus } from '@/constants/issue-collection';
import { issueCollectionApi } from '@/service/api';
import MarkdownEditor from '@/components/MarkdownEditor.vue';

defineOptions({
  name: 'IssueCollectionCreate'
});

const router = useRouter();

const form = ref<{
  title: string;
  description: string;
}>({
  title: '',
  description: ''
});

const loading = ref(false);
const selectedTemplate = ref<string>('');

// 增强的模板选项，带图标和描述
const templateOptions = [
  {
    label: '每日问题反馈',
    value: 'daily',
    icon: 'mdi:calendar-today',
    color: '#18a058',
    description: '记录日常工作中的问题和反馈',
    template: `# 每日问题反馈

**📅 日期**：${new Date().toLocaleDateString('zh-CN')}
**👤 反馈人**：XXX

---

## 🐛 问题列表

### 1. 问题描述标题

**影响范围**：
- 用户群体：XXX
- 影响程度：高/中/低

**详细描述**：
具体描述问题的表现、复现步骤等...

**期望结果**：
描述期望的正确行为

---

### 2. 另一个问题

按照上述格式继续添加...

---

## 📝 备注

（可选的补充信息和附件）`
  },
  {
    label: '现场问题收集',
    value: 'field',
    icon: 'mdi:map-marker',
    color: '#f0a020',
    description: '收集现场环境中的问题和建议',
    template: `# 现场问题收集

**📍 现场地点**：XXX
**⏰ 收集时间**：${new Date().toLocaleString('zh-CN')}
**👨‍💻 收集人**：XXX

---

## 🔴 高优先级问题

### 问题1：登录问题
- **现象**：用户反馈登录时出现错误
- **影响**：无法正常使用系统
- **频率**：偶发/频发

---

## 🟡 中优先级问题

### 问题1：性能问题
- **现象**：页面加载缓慢
- **影响**：用户体验下降
- **频率**：持续

---

## 🔵 功能建议

### 建议1：增加XXX功能
- **需求背景**：XXX
- **使用场景**：XXX
- **优先级**：低

---

## 📋 优先级说明

- 🔴 **高优先级**：影响正常使用的问题
- 🟡 **中优先级**：影响用户体验的问题
- 🔵 **低优先级**：功能优化建议`
  },
  {
    label: '功能优化建议',
    value: 'feature',
    icon: 'mdi:lightbulb',
    color: '#2080f0',
    description: '收集产品功能改进建议',
    template: `# 功能优化建议

**📝 提交时间**：${new Date().toLocaleString('zh-CN')}
**💡 建议类型**：功能优化

---

## 🎯 核心建议

### 建议1：[具体功能名称]

**当前问题**：
描述当前功能存在的不足或痛点

**改进方案**：
\`\`\`
详细描述改进方案，包括：
- 用户价值
- 实现思路
- 预期效果
\`\`\`

**优先级**：高/中/低
**预期收益**：XXX

---

## 🎨 体验优化

### 优化1：[具体优化点]

**现状**：XXX
**建议**：XXX
**收益**：XXX

---

## 📊 数据支持

（如果有数据或用户反馈支持，请在此添加）
- 用户反馈次数：XX
- 影响用户数：XX
- 用户痛点评分：X/5

---

## 🔗 相关资源

- 竞品参考：XXX
- 设计稿：XXX
- 技术文档：XXX`
  },
  {
    label: '技术债务记录',
    value: 'tech',
    icon: 'mdi:code-braces',
    color: '#7c4dff',
    description: '记录需要重构或优化的技术问题',
    template: `# 技术债务记录

**📅 记录日期**：${new Date().toLocaleDateString('zh-CN')}
**👨‍💻 负责人**：XXX
**🏷️ 模块**：XXX

---

## ⚠️ 高优先级技术债务

### 债务1：[问题描述]

**类型**：
- [ ] 性能问题
- [ ] 代码质量
- [ ] 安全问题
- [ ] 架构设计
- [ ] 依赖升级

**现状**：
\`\`\`
当前实现的简要说明
\`\`\`

**问题**：
\`\`\`
存在问题的具体描述
\`\`\`

**建议方案**：
\`\`\`
重构或优化的具体方案
\`\`\`

**预估工作量**：X人天
**优先级**：P0/P1/P2
**计划时间**：XXX

---

## 📊 影响评估

| 项目 | 影响程度 | 说明 |
|------|---------|------|
| 性能 | 高/中/低 | XXX |
| 可维护性 | 高/中/低 | XXX |
| 安全性 | 高/中/低 | XXX |

---

## 🔄 处理计划

- [ ] 分析问题
- [ ] 设计方案
- [ ] 评审通过
- [ ] 实施优化
- [ ] 测试验证
- [ ] 上线发布`
  }
];

// 预览内容
// 应用模板
function applyTemplate(option: (typeof templateOptions)[0]) {
  selectedTemplate.value = option.value;
  form.value.description = option.template;
  window.$message?.success(`已应用"${option.label}"模板`);
}

// 提交表单
async function handleSubmit() {
  if (!form.value.title.trim()) {
    window.$message?.warning('请输入标题');
    return;
  }

  loading.value = true;
  try {
    const response = await issueCollectionApi.createCollection({
      title: form.value.title,
      description: form.value.description || undefined,
      status: CollectionStatus.PENDING
    });

    if (response.data?.id) {
      window.$message?.success('创建成功！正在跳转...');
      setTimeout(() => {
        router.push(`/issue/collection/${response.data.id}`);
      }, 500);
    }
  } catch {
    window.$message?.error('创建失败，请重试');
  } finally {
    loading.value = false;
  }
}

// 取消
function handleCancel() {
  router.back();
}
</script>

<template>
  <div class="h-full overflow-hidden p-4">
    <div class="create-page-layout">
      <!-- 左侧：主表单区域 -->
      <div class="main-section">
        <NCard title="创建问题集" class="h-full rounded-16px shadow-sm">
          <!-- 表单 -->
          <NForm label-placement="top" :show-feedback="false">
            <NFormItem label="标题">
              <NInput
                v-model:value="form.title"
                placeholder="例如：2026-03-12 现场问题反馈"
                maxlength="255"
                show-count
                size="large"
                clearable
              />
            </NFormItem>

            <!-- Markdown 编辑器 -->
            <NFormItem label="描述内容">
              <MarkdownEditor
                v-model="form.description"
                placeholder="请输入问题描述，支持 Markdown 格式..."
                :rows="6"
              />
            </NFormItem>
          </NForm>

          <NDivider />

          <!-- 操作按钮 -->
          <NSpace justify="end" :size="12">
            <NButton @click="handleCancel">
              <NIcon class="mr-1"><icon-mdi-close /></NIcon>
              取消
            </NButton>
            <NButton type="primary" size="large" :loading="loading" @click="handleSubmit">
              <NIcon class="mr-1"><icon-mdi-check /></NIcon>
              创建问题集
            </NButton>
          </NSpace>
        </NCard>
      </div>

      <!-- 右侧：快捷模板 -->
      <div class="side-section">
        <NCard title="📋 快捷模板" size="small" class="template-card shadow-sm">
          <!--
 <template #header-extra>
            <NButton
              v-if="selectedTemplate"
              text
              size="small"
              type="error"
              @click="clearTemplate"
            >
              <NIcon class="mr-1" size="14"><icon-mdi-close /></NIcon>
              清除
            </NButton>
          </template> 
-->

          <NSpace vertical :size="12">
            <div
              v-for="option in templateOptions"
              :key="option.value"
              class="template-item"
              :class="{ active: selectedTemplate === option.value }"
              @click="applyTemplate(option)"
            >
              <div class="template-icon" :style="{ backgroundColor: option.color + '20', color: option.color }">
                <span class="template-emoji">
                  {{
                    option.value === 'daily'
                      ? '📅'
                      : option.value === 'field'
                        ? '📍'
                        : option.value === 'feature'
                          ? '💡'
                          : '🔧'
                  }}
                </span>
              </div>
              <div class="template-info">
                <div class="template-label">{{ option.label }}</div>
                <div class="template-desc">{{ option.description }}</div>
              </div>
            </div>
          </NSpace>
        </NCard>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-page-layout {
  display: flex;
  gap: 16px;
  height: 100%;
}

.main-section {
  flex: 1;
  min-width: 0;
}

.side-section {
  width: 320px;
  flex-shrink: 0;
}

/* 模板卡片样式 */
.template-card {
  height: fit-content;
}

.template-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  border: 2px solid transparent;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.3s ease;
}

.template-item:hover {
  background: #f1f5f9;
  border-color: #e2e8f0;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.template-item.active {
  background: #eff6ff;
  border-color: var(--color-primary);
}

.template-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.template-emoji {
  font-size: 24px;
}

.template-info {
  flex: 1;
  min-width: 0;
}

.template-label {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
  margin-bottom: 2px;
}

.template-desc {
  font-size: 12px;
  color: #64748b;
  line-height: 1.4;
}

.mr-1 {
  margin-right: 4px;
}

/* MarkdownEditor 宽度设置 */
:deep(.n-form-item-blank) {
  width: 100%;
}

:deep(.markdown-editor) {
  width: 100%;
}

/* 编辑/预览切换 - Segment 风格 */
.editor-preview-toggle {
  margin-bottom: 16px;
}

.toggle-container {
  display: inline-flex;
  background: #f1f5f9;
  border-radius: 12px;
  padding: 4px;
  gap: 4px;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05);
}

.toggle-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
  user-select: none;
}

.toggle-item:hover {
  color: #475569;
  background: rgba(255, 255, 255, 0.5);
}

.toggle-item.active {
  background: white;
  color: var(--color-primary);
  box-shadow:
    0 2px 8px rgba(59, 130, 246, 0.15),
    0 1px 3px rgba(0, 0, 0, 0.1);
}

.toggle-item .n-icon {
  transition: transform 0.3s ease;
}

.toggle-item.active .n-icon {
  transform: scale(1.1);
}

.editor-section,
.preview-section {
  min-height: 400px;
}

.preview-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 12px;
  font-weight: 600;
}

.preview-content {
  padding: 20px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid var(--color-border-subtle);
  min-height: 300px;
  line-height: 1.8;
  color: #374151;
}

.markdown-body {
  font-size: 14px;
}

/* 工具类 */
.mr-1 {
  margin-right: 4px;
}
</style>
