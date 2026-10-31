<script setup lang="ts">
/**
 * AI 助手悬浮组件
 *
 * 交互设计:
 * - 默认：小机器人半圆形按钮贴在右边缘
 * - 点击：展开成圆形聊天窗口
 * - 再次点击：收起回小图标
 * - 支持放大/缩小窗口
 * - 一键全屏/还原（类似微信网页版）
 * - 流畅的展开/收起动画
 *
 * ⭐ Token 传递：
 * - 从 OpenTask localStorage 获取 token
 * - 作为 URL 参数传递给 ChatApp iframe
 * - 解决跨域问题
 */

import { computed, ref } from 'vue';
import { Icon } from '@iconify/vue';
import { localStg } from '@/utils/storage';

// ⭐ ChatApp 前端 URL
const CHATAPP_URL = import.meta.env.VITE_CHATAPP_URL || 'http://localhost:5173';

// 展开状态
const isExpanded = ref(false);

// 窗口大小状态：small | medium | large | fullscreen
const windowSize = ref<'small' | 'medium' | 'large' | 'fullscreen'>('medium');

// ⭐ ChatApp iframe URL（带 token 参数）
const chatappUrl = computed(() => {
  const token = localStg.get('token');
  if (token) {
    // 携带 token 作为 URL 参数
    // return `${CHATAPP_URL}?token=${encodeURIComponent(token)}`
    return `${CHATAPP_URL}?token=${token}`;
  }
  return CHATAPP_URL;
});

// 切换展开/收起
const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};

// 收起
const collapse = () => {
  isExpanded.value = false;
};

// 放大窗口
const enlarge = () => {
  if (windowSize.value === 'small') {
    windowSize.value = 'medium';
  } else if (windowSize.value === 'medium') {
    windowSize.value = 'large';
  }
};

// 缩小窗口
const shrink = () => {
  if (windowSize.value === 'fullscreen') {
    // 从全屏缩小到大窗口
    windowSize.value = 'large';
  } else if (windowSize.value === 'large') {
    windowSize.value = 'medium';
  } else if (windowSize.value === 'medium') {
    windowSize.value = 'small';
  }
};

// 切换全屏/还原
const toggleFullscreen = () => {
  if (windowSize.value === 'fullscreen') {
    // 从全屏还原到中尺寸
    windowSize.value = 'medium';
  } else {
    // 进入全屏模式
    windowSize.value = 'fullscreen';
  }
};

// 计算窗口类名
const windowClass = computed(() => {
  return `size-${windowSize.value}`;
});

// 判断是否处于全屏模式
const isFullscreen = computed(() => {
  return windowSize.value === 'fullscreen';
});

// 判断是否可以放大
const canEnlarge = computed(() => {
  return windowSize.value !== 'fullscreen';
});

// 判断是否可以缩小
const canShrink = computed(() => {
  return windowSize.value !== 'small';
});

// iframe 加载完成
const onIframeLoad = () => {};
</script>

<template>
  <!-- AI 助手容器 -->
  <div class="ai-assistant-container" :class="{ expanded: isExpanded }">
    <!-- 折叠状态：小机器人按钮 -->
    <div v-if="!isExpanded" class="robot-button" @click="toggleExpand">
      <!-- 机器人图标 -->
      <div class="robot-icon-wrapper">
        <Icon icon="lucide:bot" :width="32" :height="32" class="robot-icon" />
      </div>

      <!-- 悬停提示 -->
      <div class="tooltip">AI 智能助手</div>

      <!-- 脉冲动画 -->
      <div class="pulse-ring"></div>
    </div>

    <!-- 展开状态：聊天窗口 -->
    <Transition name="chat-window">
      <div v-if="isExpanded" class="chat-window" :class="windowClass">
        <!-- 窗口头部 -->
        <div class="chat-header">
          <div class="header-content">
            <div class="robot-avatar">
              <Icon icon="lucide:bot" :width="18" :height="18" />
            </div>
            <div class="header-text">
              <div class="header-title">AI 智能助手</div>
            </div>
          </div>
          <div class="header-actions">
            <!-- 缩小按钮 -->
            <button class="action-btn size-btn" :disabled="!canShrink" title="缩小" @click="shrink">
              <Icon icon="lucide:minus" :width="12" :height="12" />
            </button>
            <!-- 放大按钮 -->
            <button class="action-btn size-btn" :disabled="!canEnlarge" title="放大" @click="enlarge">
              <Icon icon="lucide:plus" :width="12" :height="12" />
            </button>
            <!-- 一键全屏按钮 -->
            <button
              class="action-btn fullscreen-btn"
              :title="isFullscreen ? '退出全屏' : '全屏'"
              @click="toggleFullscreen"
            >
              <Icon :icon="isFullscreen ? 'lucide:minimize' : 'lucide:maximize'" :width="14" :height="14" />
            </button>
            <!-- 关闭按钮 -->
            <button class="action-btn close-btn" title="关闭" @click="collapse">
              <Icon icon="lucide:x" :width="12" :height="12" />
            </button>
          </div>
        </div>

        <!-- 聊天内容区域 -->
        <div class="chat-content">
          <iframe
            :src="chatappUrl"
            frameborder="0"
            class="chat-iframe"
            allow="microphone; camera"
            @load="onIframeLoad"
          ></iframe>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped lang="scss">
/* ==================== 容器 ==================== */
.ai-assistant-container {
  position: fixed;
  right: 0;
  bottom: 80px;
  z-index: 9999;
  transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

/* ==================== 折叠状态：机器人按钮 ==================== */
.robot-button {
  position: absolute;
  right: 0;
  width: 56px;
  height: 56px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    transform: scale(1.1);
    .robot-icon-wrapper {
      transform: rotate(10deg) scale(1.1);
    }
  }

  &:active {
    transform: scale(0.95);
  }
}

/* 机器人图标容器 */
.robot-icon-wrapper {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50% 0 0 50%; /* 半圆形 */
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;

  .robot-icon {
    color: #fff;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
  }
}

/* 悬停提示 */
.tooltip {
  position: absolute;
  right: 64px;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
  pointer-events: none;

  &::after {
    content: '';
    position: absolute;
    right: -5px;
    top: 50%;
    transform: translateY(-50%);
    width: 0;
    height: 0;
    border-left: 5px solid rgba(0, 0, 0, 0.8);
    border-top: 5px solid transparent;
    border-bottom: 5px solid transparent;
  }
}

.robot-button:hover .tooltip {
  opacity: 1;
  visibility: visible;
  right: 68px;
}

/* 脉冲动画 */
.pulse-ring {
  position: absolute;
  top: 50%;
  right: 50%;
  transform: translate(50%, -50%);
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 2px solid #667eea;
  opacity: 0;
  animation: pulse 2s ease-out infinite;
  pointer-events: none;
}

@keyframes pulse {
  0% {
    transform: translate(50%, -50%) scale(1);
    opacity: 0.6;
  }

  100% {
    transform: translate(50%, -50%) scale(1.8);
    opacity: 0;
  }
}

/* ==================== 展开状态：聊天窗口 ==================== */
.chat-window {
  background: #fff;
  border-radius: 16px 0 0 16px;
  box-shadow: -4px 0 32px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin-right: 0;
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);

  /* 四种尺寸 */
  &.size-small {
    width: 380px;
    height: 520px;
  }

  &.size-medium {
    width: 450px;
    height: 600px;
  }

  &.size-large {
    width: 550px;
    height: 700px;
  }

  &.size-fullscreen {
    width: 75%;
    height: calc(100vh - 80px); // 减去header高度和一些边距
    position: fixed;
    right: 20px;
    bottom: 20px;
    border-radius: 16px;
    box-shadow: 0 8px 48px rgba(0, 0, 0, 0.25);
    transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  }
}

/* Transition 过渡动画 - 只保留进入动画 */
.chat-window-enter-active {
  transition: all 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

.chat-window-leave-active {
  transition: none;
}

.chat-window-enter-from {
  transform: translateX(120%) scale(0.3) rotate(-5deg);
  opacity: 0;
}

.chat-window-leave-to {
  opacity: 0;
  visibility: hidden;
}

/* 窗口头部 */
.chat-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
  flex-shrink: 0;

  .header-content {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;

    .robot-avatar {
      width: 32px;
      height: 32px;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      backdrop-filter: blur(10px);
      flex-shrink: 0;
    }
  }

  .header-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
    align-items: center;

    /* 操作按钮通用样式 */
    .action-btn {
      background: rgba(255, 255, 255, 0.2);
      border: none;
      color: #fff;
      width: 24px;
      height: 24px;
      padding: 0;
      flex-shrink: 0;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;

      &:hover:not(:disabled) {
        background: rgba(255, 255, 255, 0.3);
        transform: scale(1.1);
      }

      &:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
    }

    /* 一键全屏按钮 - 突出显示 */
    .fullscreen-btn {
      background: rgba(255, 255, 255, 0.3);
      border: 2px solid rgba(255, 255, 255, 0.5);
      width: 28px;
      height: 28px;
      font-weight: bold;

      &:hover {
        background: rgba(255, 255, 255, 0.4);
        border-color: rgba(255, 255, 255, 0.8);
        transform: scale(1.15);
        box-shadow: 0 4px 12px rgba(255, 255, 255, 0.3);
      }
    }

    .close-btn:hover {
      transform: rotate(90deg);
    }
  }
}

/* 聊天内容区域 */
.chat-content {
  flex: 1;
  position: relative;
  background: #f5f7fa;
  overflow: hidden;

  .chat-iframe {
    width: 100%;
    height: 100%;
    border: none;
  }
}

/* 底部提示 */
.chat-footer {
  background: #fff;
  padding: 8px 14px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
  text-align: center;

  :deep(.el-text) {
    font-size: 12px;
  }
}

/* ==================== 响应式调整 ==================== */
@media (max-width: 768px) {
  .ai-assistant-container {
    bottom: 16px;
  }

  .robot-button {
    width: 52px;
    height: 52px;
  }

  .chat-window {
    &.size-small {
      width: calc(100vw - 16px);
      height: 60vh;
    }

    &.size-medium {
      width: calc(100vw - 16px);
      height: 70vh;
    }

    &.size-large {
      width: calc(100vw - 16px);
      height: 80vh;
    }

    &.size-fullscreen {
      width: calc(100vw - 16px);
      height: calc(100vh - 80px);
      right: 8px;
      bottom: 8px;
    }
  }

  .tooltip {
    display: none; /* 移动端不显示提示 */
  }

  .header-actions {
    gap: 4px;

    .fullscreen-btn {
      width: 26px;
      height: 26px;
    }

    .action-btn {
      width: 22px;
      height: 22px;
    }
  }
}
</style>
