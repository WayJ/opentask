<!-- frontend/src/views/workflow/requirement-detail/components/CommentsCard.vue -->
<script setup lang="ts">
import { computed, ref } from 'vue';
import { NAvatar, NButton, NCard, NDivider, NSpin, NText } from 'naive-ui';
import type { RequirementComment } from '@/service/api/requirement';
import MarkdownEditor from '@/components/MarkdownEditor.vue';
import CommentDisplay from '@/components/CommentDisplay.vue';

interface Props {
  comments: RequirementComment[];
  requirementId: string;
  loading?: boolean;
}

interface Emits {
  (e: 'add', content: string): void;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});
const emit = defineEmits<Emits>();

const newComment = ref('');
const showAll = ref(false);

const displayedComments = computed(() => {
  if (showAll.value) {
    return props.comments;
  }
  return props.comments.slice(0, 5);
});

const handleSubmit = () => {
  if (!newComment.value.trim()) return;
  emit('add', newComment.value);
  newComment.value = '';
};

const formatDateTime = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN');
};

const getUserName = (comment: RequirementComment) => {
  // 优先显示 jnpf_name，如果为空则显示 name
  const jnpfName = comment.user_info?.jnpf_name;
  const name = comment.user_info?.name;
  return jnpfName || name || '未知用户';
};
</script>

<template>
  <NCard class="comments-card" :title="`💬 评论 (${comments.length})`">
    <!-- 评论列表 -->
    <NSpin :show="loading">
      <div v-if="comments.length > 0" class="comments-list">
        <div v-for="comment in displayedComments" :key="comment.id" class="comment-item">
          <div class="comment-avatar">
            <NAvatar round :size="32">
              {{ getUserName(comment)[0] }}
            </NAvatar>
          </div>
          <div class="comment-content">
            <div class="comment-header">
              <div class="user-info">
                <NText strong>{{ getUserName(comment) }}</NText>
                <NText depth="3" style="font-size: 12px">
                  {{ formatDateTime(comment.created_at) }}
                </NText>
              </div>
            </div>
            <!-- 使用 CommentDisplay 组件 -->
            <CommentDisplay :content="comment.content" :embedded-tasks="comment.embedded_tasks" />
          </div>
        </div>

        <!-- 显示更多按钮 -->
        <div v-if="!showAll && comments.length > 5" class="show-more">
          <NButton text type="primary" @click="showAll = true">查看全部 {{ comments.length }} 条评论</NButton>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="no-comments">
        <NText depth="3">暂无评论，发表第一条评论吧~</NText>
      </div>
    </NSpin>

    <NDivider />

    <!-- 评论编辑器 -->
    <div class="comment-editor">
      <MarkdownEditor v-model="newComment" placeholder="添加评论..." :rows="3" />
      <div class="editor-actions">
        <NButton
          type="primary"
          size="small"
          :disabled="!newComment.trim() || loading"
          :loading="loading"
          @click="handleSubmit"
        >
          发表评论
        </NButton>
      </div>
    </div>
  </NCard>
</template>

<style scoped>
.comments-card {
  box-shadow: var(--shadow-sm);
}

.comment-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.editor-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.comment-item {
  display: flex;
  gap: var(--space-md);
}

.comment-avatar {
  flex-shrink: 0;
}

.comment-content {
  flex: 1;
  min-width: 0;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-xs);
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.comment-text {
  font-size: var(--font-size-sm);
  line-height: 1.5;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.show-more {
  display: flex;
  justify-content: center;
  padding-top: var(--space-sm);
}

.no-comments {
  text-align: center;
  padding: var(--space-xl) 0;
}
</style>
