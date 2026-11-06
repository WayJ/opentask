<!-- frontend/src/views/issue/detail/components/IssueCardsDemo.vue -->
<script setup lang="ts">
import { ref } from 'vue';
import { NButton, NCard, NSpace, NTag } from 'naive-ui';
import IssueHeaderCard from './IssueHeaderCard.vue';
import DescriptionCard from './DescriptionCard.vue';
import CommentsCard from './CommentsCard.vue';

const demoIssue = ref({
  id: 'demo-issue-1',
  issue_code: 'OT-1',
  title: '示例 Issue：展示新的卡片式设计',
  status: 'open',
  priority: 'high',
  description: `这是一个示例 Issue，用于展示新的卡片式设计风格。

## 主要特点

1. **卡片式布局** - 每个功能模块都是独立的卡片
2. **CSS 变量** - 统一的设计系统
3. **视觉层次** - 清晰的信息分组
4. **现代感** - 圆角、阴影、过渡动画

## 技术栈

- Vue 3 Composition API
- TypeScript
- Naive UI 组件
- CSS 变量

您现在看到的描述卡片支持编辑功能，点击右上角的"编辑"按钮即可体验。`
});

const demoComments = ref([
  {
    id: '1',
    content: '这是一个示例评论，展示了评论卡片的新设计。',
    created_at: new Date().toISOString(),
    user_info: {
      sso_name: '张三'
    }
  },
  {
    id: '2',
    content: '新的设计看起来更现代了！',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    user_info: {
      sso_name: '李四'
    }
  }
]);

const handleRefresh = () => {
  console.log('刷新 Issue');
};

const handleUpdateDescription = (value: string) => {
  demoIssue.value.description = value;
};

const handleAddComment = (content: string, _embedded?: any[], _parentId?: string) => {
  demoComments.value.unshift({
    id: Date.now().toString(),
    content,
    created_at: new Date().toISOString(),
    user_info: {
      sso_name: '当前用户'
    }
  });
};
</script>

<template>
  <div class="issue-demo-page">
    <div class="issue-demo-container">
      <!-- 主内容区 -->
      <div class="issue-demo-main">
        <IssueHeaderCard :issue="demoIssue" @refresh="handleRefresh" />
        <DescriptionCard :issue="demoIssue" :editable="true" @update="handleUpdateDescription" />
        <CommentsCard :comments="demoComments" :issue-id="demoIssue.id" @add="handleAddComment" />
      </div>

      <!-- 侧边栏 -->
      <div class="issue-demo-sidebar">
        <NCard size="small" class="sidebar-card" :bordered="false">
          <template #header>
            <div class="card-header">
              <span class="card-icon">🎯</span>
              <span>核心属性</span>
            </div>
          </template>
          <div class="sidebar-field">
            <div class="field-label">状态</div>
            <NTag type="info" size="small">
              {{ demoIssue.status }}
            </NTag>
          </div>
          <div class="sidebar-field">
            <div class="field-label">优先级</div>
            <NTag type="warning" size="small">
              {{ demoIssue.priority }}
            </NTag>
          </div>
        </NCard>

        <NCard size="small" class="sidebar-card" :bordered="false">
          <template #header>
            <div class="card-header">
              <span class="card-icon">⚡</span>
              <span>快速操作</span>
            </div>
          </template>
          <NSpace vertical :size="8">
            <NButton block secondary type="info">获取 Agent 指令</NButton>
            <NButton block secondary>分配给自己</NButton>
            <NButton block secondary>标记完成</NButton>
          </NSpace>
        </NCard>
      </div>
    </div>
  </div>
</template>

<style scoped>
.issue-demo-page {
  min-height: 100vh;
  background: var(--color-bg-secondary);
  padding: var(--space-xl);
}

.issue-demo-container {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: var(--space-xl);
  align-items: start;
}

.issue-demo-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
  min-width: 0;
}

.issue-demo-sidebar {
  position: sticky;
  top: var(--space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.sidebar-card {
  box-shadow: var(--shadow-sm);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.card-icon {
  font-size: 18px;
}

.sidebar-field {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-sm) 0;
}

.field-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

@media (max-width: 1200px) {
  .issue-demo-container {
    grid-template-columns: 1fr;
  }

  .issue-demo-sidebar {
    position: static;
  }
}

@media (max-width: 768px) {
  .issue-demo-page {
    padding: var(--space-md);
  }

  .issue-demo-container {
    gap: var(--space-lg);
  }

  .issue-demo-main {
    gap: var(--space-lg);
  }
}
</style>
