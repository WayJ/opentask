<script setup lang="ts">
import { ref, watch } from 'vue';
import { NEmpty, NModal, NSpin, NTag, useMessage } from 'naive-ui';

defineOptions({
  name: 'ConversationViewer'
});

interface Props {
  show: boolean;
  fileUrl: string;
  fileName: string;
}

interface ConversationMessage {
  type: string;
  timestamp?: string;
  content: any;
  uuid?: string;
  index: number;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: 'update:show', value: boolean): void;
}>();

const message = useMessage();
const loading = ref(false);
const messages = ref<ConversationMessage[]>([]);
const error = ref<string | null>(null);

// 解析 JSONL 内容
const parseJsonl = (content: string): ConversationMessage[] => {
  const lines = content.trim().split('\n');
  return lines
    .map((line, index) => {
      try {
        const json = JSON.parse(line);
        // 提取消息内容
        let msgContent = json.message?.content || json.content || json;

        // 如果是 assistant 类型的工具调用，特殊处理
        if (json.type === 'assistant' || json.message?.role === 'assistant') {
          if (Array.isArray(msgContent)) {
            // 提取文本内容
            const textParts = msgContent
              .filter((c: any) => c.type === 'text')
              .map((c: any) => c.text)
              .join('\n');
            msgContent = textParts || JSON.stringify(msgContent, null, 2);
          }
        }

        return {
          type: json.type || json.message?.role || 'unknown',
          timestamp: json.timestamp,
          content: msgContent,
          uuid: json.uuid,
          index
        };
      } catch {
        return null;
      }
    })
    .filter(Boolean) as ConversationMessage[];
};

// 格式化消息内容显示
const formatContent = (msg: ConversationMessage): string => {
  if (typeof msg.content === 'string') {
    return msg.content;
  }
  if (typeof msg.content === 'object') {
    return JSON.stringify(msg.content, null, 2);
  }
  return String(msg.content);
};

// 获取消息类型标签类型
const getTagType = (type: string) => {
  switch (type) {
    case 'user':
      return 'primary';
    case 'assistant':
      return 'success';
    case 'tool':
      return 'warning';
    default:
      return 'default';
  }
};

// 获取消息类型显示名称
const getTypeName = (type: string): string => {
  switch (type) {
    case 'user':
      return '用户';
    case 'assistant':
      return '助手';
    case 'tool':
      return '工具';
    default:
      return type;
  }
};

// 格式化时间戳
const formatTime = (timestamp?: string): string => {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch {
    return timestamp;
  }
};

// 加载对话内容
const loadConversation = async () => {
  loading.value = true;
  error.value = null;
  messages.value = [];

  try {
    const response = await fetch(props.fileUrl);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const content = await response.text();
    messages.value = parseJsonl(content);

    if (messages.value.length === 0) {
      error.value = '未找到有效的对话记录';
    }
  } catch (e: any) {
    console.error('加载对话失败:', e);
    error.value = e.message || '加载对话失败';
    message.error(error.value);
  } finally {
    loading.value = false;
  }
};

// 监听显示状态
watch(
  () => props.show,
  show => {
    if (show) {
      loadConversation();
    }
  }
);
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :style="{ width: '85%', maxWidth: '1000px' }"
    :title="`对话记录 - ${fileName}`"
    :segmented="{ content: 'soft' }"
    @update:show="emit('update:show', $event)"
  >
    <div class="conversation-viewer">
      <NSpin :show="loading" description="加载中...">
        <div v-if="error" class="error-container">
          <NEmpty :description="error" />
        </div>

        <div v-else-if="messages.length > 0" class="messages">
          <div v-for="msg in messages" :key="msg.uuid || msg.index" class="message" :class="[`message--${msg.type}`]">
            <div class="message-header">
              <NTag :type="getTagType(msg.type)" size="small">
                {{ getTypeName(msg.type) }}
              </NTag>
              <span v-if="msg.timestamp" class="message-time">
                {{ formatTime(msg.timestamp) }}
              </span>
            </div>
            <div class="message-content">
              <pre>{{ formatContent(msg) }}</pre>
            </div>
          </div>
        </div>

        <NEmpty v-else description="暂无对话记录" />
      </NSpin>
    </div>
  </NModal>
</template>

<style scoped>
.conversation-viewer {
  max-height: 70vh;
  overflow-y: auto;
}

.error-container {
  padding: 40px 0;
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--n-color-modal);
  border-left: 4px solid;
  transition: background-color 0.2s;
}

.message:hover {
  background: var(--n-hover-color);
}

.message--user {
  border-left-color: #18a058;
}

.message--assistant {
  border-left-color: #2080f0;
}

.message--tool {
  border-left-color: #f0a020;
}

.message--unknown {
  border-left-color: #909399;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.message-time {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.message-content {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--n-text-color-1);
}

.message-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
