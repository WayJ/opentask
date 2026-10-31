<script setup lang="ts">
import { ref, watch } from 'vue';
import { NButton, NDropdown, NPopover, NSpace, NText } from 'naive-ui';

interface Reaction {
  emoji: string;
  name: string;
  count: number;
  users: string[];
  reacted: boolean;
}

interface Props {
  modelValue: Record<string, string[]>;
  disabled?: boolean;
  currentUserId?: string;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  currentUserId: ''
});

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, string[]>];
  react: [emoji: string];
  unreact: [emoji: string];
}>();

// 可用的表情
const availableReactions = [
  { emoji: '👍', name: '赞成' },
  { emoji: '👎', name: '反对' },
  { emoji: '❤️', name: '喜欢' },
  { emoji: '🎉', name: '庆祝' },
  { emoji: '🚀', name: '火箭' },
  { emoji: '👀', name: '关注' },
  { emoji: '😕', name: '困惑' },
  { emoji: '😄', name: '开心' }
];

// 计算反应列表
const reactions = ref<Reaction[]>([]);

// 更新反应列表
function updateReactions() {
  reactions.value = availableReactions.map(reaction => {
    const users = props.modelValue[reaction.emoji] || [];
    return {
      emoji: reaction.emoji,
      name: reaction.name,
      count: users.length,
      users,
      reacted: props.currentUserId ? users.includes(props.currentUserId) : false
    };
  });
}

// 监听 modelValue 变化
// eslint-disable-next-line @typescript-eslint/no-unused-vars
watch(
  () => props.modelValue,
  () => {
    updateReactions();
  },
  { immediate: true }
);

// 处理反应点击
function handleReactionClick(emoji: string) {
  if (props.disabled || !props.currentUserId) return;

  const reaction = reactions.value.find(r => r.emoji === emoji);
  if (!reaction) return;

  const currentValue = props.modelValue[emoji] || [];
  const hasReacted = currentValue.includes(props.currentUserId);

  if (hasReacted) {
    // 取消反应
    const newValue = currentValue.filter(u => u !== props.currentUserId);
    emit('unreact', emoji);
    emit('update:modelValue', {
      ...props.modelValue,
      [emoji]: newValue
    });
  } else {
    // 添加反应
    const newValue = [...currentValue, props.currentUserId];
    emit('react', emoji);
    emit('update:modelValue', {
      ...props.modelValue,
      [emoji]: newValue
    });
  }
}

// 获取反应用户的显示文本
function getReactionUsersText(reaction: Reaction): string {
  if (reaction.count === 0) return '';
  if (reaction.count <= 2) {
    return reaction.users.join(', ');
  }
  return `${reaction.users[0]}, ${reaction.users[1]} 和其他 ${reaction.count - 2} 人`;
}
</script>

<template>
  <div class="issue-reactions">
    <NSpace :size="8">
      <!-- 现有反应 -->
      <div
        v-for="reaction in reactions.filter(r => r.count > 0)"
        :key="reaction.emoji"
        class="reaction-item"
        :class="[reaction.reacted ? 'reaction-item-reacted' : '', disabled ? 'reaction-item-disabled' : '']"
        @click="handleReactionClick(reaction.emoji)"
      >
        <span class="reaction-emoji">{{ reaction.emoji }}</span>
        <span class="reaction-count">{{ reaction.count }}</span>
      </div>

      <!-- 添加反应按钮 -->
      <NDropdown
        v-if="!disabled"
        :options="availableReactions.map(r => ({ label: `${r.emoji} ${r.name}`, key: r.emoji }))"
        placement="top"
        trigger="click"
        @select="key => handleReactionClick(key as string)"
      >
        <NButton text size="small" class="reaction-add-button">
          <template #icon>
            <icon-mdi-emoticon-happy-outline />
          </template>
          添加反应
        </NButton>
      </NDropdown>

      <!-- 显示所有反应的用户 -->
      <NPopover v-if="reactions.some(r => r.count > 0)" trigger="hover" placement="top">
        <template #trigger>
          <NButton text size="small" class="reaction-users-button">
            <icon-mdi-account-multiple-outline />
          </NButton>
        </template>
        <div class="reaction-users-list">
          <div v-for="reaction in reactions.filter(r => r.count > 0)" :key="reaction.emoji" class="reaction-user-item">
            <span class="reaction-emoji">{{ reaction.emoji }}</span>
            <NText>{{ getReactionUsersText(reaction) }}</NText>
          </div>
        </div>
      </NPopover>
    </NSpace>
  </div>
</template>

<style scoped>
.issue-reactions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 0;
  border-top: 1px solid #f0f0f0;
}

.reaction-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.reaction-item:hover {
  background: #e8e8e8;
  border-color: #d0d0d0;
}

.reaction-item-reacted {
  background: #e6f0ff;
  border-color: #646cff;
}

.reaction-item-disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.reaction-item-disabled:hover {
  background: #f5f5f5;
  border-color: #e0e0e0;
}

.reaction-emoji {
  font-size: 16px;
  line-height: 1;
}

.reaction-count {
  font-size: 13px;
  font-weight: 500;
  color: #24292f;
}

.reaction-add-button {
  padding: 4px 12px;
  border: 1px dashed #d0d0d0;
  border-radius: 20px;
  color: #666;
}

.reaction-add-button:hover {
  border-color: #646cff;
  color: #646cff;
}

.reaction-users-button {
  padding: 4px 8px;
  color: #666;
}

.reaction-users-list {
  min-width: 200px;
  max-width: 400px;
}

.reaction-user-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
}

.reaction-user-item:not(:last-child) {
  border-bottom: 1px solid #f0f0f0;
}
</style>
