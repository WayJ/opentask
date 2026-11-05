<!-- frontend/src/views/issue/detail/components/CommentsCard.vue -->
<script setup lang="ts">
import { computed, ref } from 'vue';
import { NAvatar, NButton, NCard, NDivider, NText } from 'naive-ui';
import MarkdownEditor from '@/components/MarkdownEditor.vue';
import CommentDisplay from '@/components/CommentDisplay.vue';
import AttachmentList from '@/components/common/AttachmentList.vue';
import { commentAttachmentToDocument } from '@/utils/attachmentUrls';
import { buildCommentTree } from '@/utils/buildCommentTree';

interface CommentAttachment {
  id: string;
  file_name: string;
  file_size: number;
  file_type: string;
}

interface Comment {
  id: string;
  content: string;
  created_at: string;
  parent_id?: string | null;
  user_info?: {
    sso_name?: string;
  };
  attachments?: CommentAttachment[];
  embedded_tasks?: any[];
}

interface Props {
  comments: Comment[];
  issueId: string;
}

interface Emits {
  (e: 'add', content: string, embeddedTasks?: any[], parentId?: string): void;
  (e: 'refresh'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const newComment = ref('');
const showAll = ref(false);
const embeddedTasks = ref<any[]>([]);
const replyToId = ref<string | null>(null);
const replyToPreview = ref('');

const commentTree = computed(() => buildCommentTree(props.comments));

const displayedTree = computed(() => {
  if (showAll.value) return commentTree.value;
  // Cap by root count for "show more"
  return commentTree.value.slice(0, 5);
});

const handleSubmit = () => {
  if (!newComment.value.trim()) return;
  emit('add', newComment.value, embeddedTasks.value, replyToId.value || undefined);
  newComment.value = '';
  embeddedTasks.value = [];
  replyToId.value = null;
  replyToPreview.value = '';
};

function handleTaskEmbedded(task: any) {
  embeddedTasks.value.push(task);
}

function startReply(comment: Comment) {
  replyToId.value = comment.id;
  const name = comment.user_info?.sso_name || '';
  replyToPreview.value = name ? `回复 @${name}` : '回复评论';
}

function cancelReply() {
  replyToId.value = null;
  replyToPreview.value = '';
}

const formatDateTime = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN');
};

const getUserName = (comment: Comment) => {
  return comment.user_info?.sso_name || '未知用户';
};

function mapAttachments(comment: Comment) {
  return (comment.attachments || []).map(a => commentAttachmentToDocument(a, comment.id));
}
</script>

<template>
  <NCard class="comments-card" :title="`💬 评论 (${comments.length})`">
    <div class="comment-editor">
      <div v-if="replyToId" class="reply-banner">
        <NText depth="3" style="font-size: 12px">{{ replyToPreview }}</NText>
        <NButton text size="tiny" @click="cancelReply">取消</NButton>
      </div>
      <MarkdownEditor
        v-model="newComment"
        source-type="issue"
        :source-id="issueId"
        :placeholder="replyToId ? '写下回复...' : '添加评论... 输入 / 唤起命令'"
        :rows="3"
        @task-embedded="handleTaskEmbedded"
      />
      <div class="editor-actions">
        <NButton type="primary" size="small" :disabled="!newComment.trim()" @click="handleSubmit">
          {{ replyToId ? '发表回复' : '发表评论' }}
        </NButton>
      </div>
    </div>

    <NDivider />

    <div class="comments-list">
      <template v-for="node in displayedTree" :key="node.comment.id">
        <div class="comment-item">
          <div class="comment-avatar">
            <NAvatar round :size="32">
              {{ getUserName(node.comment)[0] }}
            </NAvatar>
          </div>
          <div class="comment-content">
            <div class="comment-header">
              <div class="user-info">
                <NText strong>{{ getUserName(node.comment) }}</NText>
                <NText depth="3" style="font-size: 12px">
                  {{ formatDateTime(node.comment.created_at) }}
                </NText>
              </div>
              <NButton text size="tiny" @click="startReply(node.comment)">回复</NButton>
            </div>
            <div class="comment-text">
              <CommentDisplay :content="node.comment.content" :embedded-tasks="node.comment.embedded_tasks" />
            </div>
            <div class="comment-attachments">
              <AttachmentList
                :issue-id="issueId"
                :comment-id="node.comment.id"
                :attachments="mapAttachments(node.comment)"
                @refresh="emit('refresh')"
              />
            </div>
          </div>
        </div>
        <div
          v-for="reply in node.replies"
          :key="reply.id"
          class="comment-item comment-reply"
          style="margin-left: 28px"
        >
          <div class="comment-avatar">
            <NAvatar round :size="28">
              {{ getUserName(reply)[0] }}
            </NAvatar>
          </div>
          <div class="comment-content">
            <div class="comment-header">
              <div class="user-info">
                <NText strong>{{ getUserName(reply) }}</NText>
                <NText depth="3" style="font-size: 12px">
                  {{ formatDateTime(reply.created_at) }}
                </NText>
              </div>
            </div>
            <div class="comment-text">
              <CommentDisplay :content="reply.content" :embedded-tasks="reply.embedded_tasks" />
            </div>
            <div class="comment-attachments">
              <AttachmentList
                :issue-id="issueId"
                :comment-id="reply.id"
                :attachments="mapAttachments(reply)"
                @refresh="emit('refresh')"
              />
            </div>
          </div>
        </div>
      </template>
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

.reply-banner {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-actions {
  display: flex;
  align-items: center;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.comment-item {
  display: flex;
  gap: var(--space-sm);
}

.comment-content {
  flex: 1;
  min-width: 0;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.user-info {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.comment-attachments {
  margin-top: 8px;
}
</style>
