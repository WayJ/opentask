<!-- frontend/src/views/issue/detail/components/CommentsCard.vue -->
<script setup lang="ts">
import { computed, ref } from 'vue';
import { NAvatar, NButton, NCard, NDivider, NText } from 'naive-ui';
import MarkdownEditor from '@/components/MarkdownEditor.vue';
import CommentDisplay from '@/components/CommentDisplay.vue';

interface Comment {
  id: string;
  content: string;
  created_at: string;
  user_info?: {
    jnpf_name?: string;
  };
}

interface Props {
  comments: Comment[];
  issueId: string;
}

interface Emits {
  (e: 'add', content: string, embeddedTasks?: any[]): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const newComment = ref('');
const showAll = ref(false);
const embeddedTasks = ref<any[]>([]);

const displayedComments = computed(() => {
  if (showAll.value) {
    return props.comments;
  }
  return props.comments.slice(0, 5);
});

const handleSubmit = () => {
  if (!newComment.value.trim()) return;
  emit('add', newComment.value, embeddedTasks.value);
  newComment.value = '';
  embeddedTasks.value = [];
};

function handleTaskEmbedded(task: any) {
  embeddedTasks.value.push(task);
}

const formatDateTime = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN');
};

const getUserName = (comment: Comment) => {
  return comment.user_info?.jnpf_name || '未知用户';
};
</script>

<template>
  <NCard class="comments-card" :title="`💬 评论 (${comments.length})`">
    <div class="comment-editor">
      <MarkdownEditor
        v-model="newComment"
        source-type="issue"
        :source-id="issueId"
        placeholder="添加评论... 输入 / 唤起命令"
        :rows="3"
        @task-embedded="handleTaskEmbedded"
      />
      <div class="editor-actions">
        <NButton type="primary" size="small" :disabled="!newComment.trim()" @click="handleSubmit">发表评论</NButton>
      </div>
    </div>

    <NDivider />

    <div class="comments-list">
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
          <div class="comment-text">
            <CommentDisplay :content="comment.content" :embedded-tasks="comment.embedded_tasks" />
          </div>
        </div>
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
}
</style>
