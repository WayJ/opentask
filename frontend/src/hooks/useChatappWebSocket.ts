/**
 * ChatApp WebSocket Hook
 *
 * 管理与 ChatApp 后端的 WebSocket 连接
 * 自动携带 OpenTask 的认证 token
 */

import { useCallback, useEffect, useRef } from 'vue';
import type { ChatMessage } from '@/service/api/chatapp';

export interface ChatappWebSocketOptions {
  /** ChatApp WebSocket URL */
  url?: string;
  /** 当前聊天会话 ID */
  chatId?: string;
  /** 连接建立回调 */
  onConnected?: () => void;
  /** 收到历史消息回调 */
  onHistory?: (messages: ChatMessage[]) => void;
  /** 收到助手消息回调 */
  onAssistantMessage?: (content: string) => void;
  /** 工具使用回调 */
  onToolUse?: (toolName: string, toolInput: any) => void;
  /** 查询完成回调 */
  onResult?: (success: boolean) => void;
  /** 错误回调 */
  onError?: (error: string) => void;
  /** 连接关闭回调 */
  onDisconnected?: () => void;
}

export function useChatappWebSocket(options: ChatappWebSocketOptions = {}) {
  const {
    url = 'ws://localhost:3001/ws',
    chatId,
    onConnected,
    onHistory,
    onAssistantMessage,
    onToolUse,
    onResult,
    onError,
    onDisconnected
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isManualCloseRef = useRef(false);

  /**
   * 获取 OpenTask 的认证 token
   */
  const getToken = useCallback((): string | null => {
    // 从 localStorage 读取 token（与 OpenTask 主应用一致）
    const token = localStorage.getItem('token');
    return token;
  }, []);

  /**
   * 处理收到的消息
   */
  const handleMessage = useCallback(
    (message: any) => {
      switch (message.type) {
        case 'connected':
          console.log('[ChatApp WebSocket] Server confirmed connection');
          break;

        case 'history':
          console.log('[ChatApp WebSocket] Received history:', message.messages?.length, 'messages');
          onHistory?.(message.messages || []);
          break;

        case 'assistant_message':
          console.log('[ChatApp WebSocket] Received assistant message');
          onAssistantMessage?.(message.content);
          break;

        case 'tool_use':
          console.log('[ChatApp WebSocket] Tool use:', message.toolName);
          onToolUse?.(message.toolName, message.toolInput);
          break;

        case 'result':
          console.log('[ChatApp WebSocket] Query result:', message.success);
          onResult?.(message.success);
          break;

        case 'error':
          console.error('[ChatApp WebSocket] Server error:', message.error);
          onError?.(message.error);
          break;

        default:
          console.warn('[ChatApp WebSocket] Unknown message type:', message.type);
      }
    },
    [onHistory, onAssistantMessage, onToolUse, onResult, onError]
  );

  /**
   * 订阅聊天会话
   */
  const subscribe = useCallback((id: string) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: 'subscribe',
          chatId: id
        })
      );
      console.log('[ChatApp WebSocket] Subscribed to chat:', id);
    }
  }, []);

  /**
   * 连接 WebSocket
   */
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      // 获取 token
      const token = getToken();

      // 构建 WebSocket URL，携带 token
      const wsUrl = token ? `${url}?token=${token}` : url;

      // 创建 WebSocket 连接
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[ChatApp WebSocket] Connected');

        // 连接成功后订阅聊天会话
        if (chatId) {
          subscribe(chatId);
        }

        onConnected?.();
      };

      ws.onmessage = event => {
        try {
          const message = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error('[ChatApp WebSocket] Failed to parse message:', error);
        }
      };

      ws.onerror = event => {
        console.error('[ChatApp WebSocket] Error:', event);
      };

      ws.onclose = event => {
        console.log('[ChatApp WebSocket] Closed:', event.code, event.reason);

        // 如果不是手动关闭，尝试重连
        if (!isManualCloseRef.current) {
          // 内联重连逻辑，避免循环依赖
          if (reconnectTimerRef.current) {
            return;
          }

          reconnectTimerRef.current = setTimeout(() => {
            reconnectTimerRef.current = null;
            console.log('[ChatApp WebSocket] Reconnecting...');
            connect();
          }, 3000);
        }

        onDisconnected?.();
      };
    } catch (error) {
      console.error('[ChatApp WebSocket] Failed to connect:', error);
      onError?.('Failed to connect to server');
    }
  }, [url, chatId, getToken, onConnected, onDisconnected, onError, subscribe, handleMessage]);

  /**
   * 发送聊天消息
   */
  const sendMessage = useCallback(
    (content: string) => {
      const ws = wsRef.current;
      if (ws?.readyState === WebSocket.OPEN && chatId) {
        ws.send(
          JSON.stringify({
            type: 'chat',
            chatId,
            content
          })
        );
        console.log('[ChatApp WebSocket] Sent message to chat:', chatId);
      } else {
        onError?.('WebSocket is not connected');
      }
    },
    [chatId, onError]
  );

  /**
   * 发送 CLI 配置
   */
  const sendConfig = useCallback(
    (apiUrl: string, token: string) => {
      const ws = wsRef.current;
      if (ws?.readyState === WebSocket.OPEN && chatId) {
        ws.send(
          JSON.stringify({
            type: 'config',
            chatId,
            apiUrl,
            token
          })
        );
        console.log('[ChatApp WebSocket] Sent CLI config for chat:', chatId);
      } else {
        onError?.('WebSocket is not connected');
      }
    },
    [chatId, onError]
  );

  /**
   * 断开连接
   */
  const disconnect = useCallback(() => {
    isManualCloseRef.current = true;

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  /**
   * 重新连接
   */
  const reconnect = useCallback(() => {
    disconnect();
    isManualCloseRef.current = false;
    connect();
  }, [disconnect, connect]);

  // 组件卸载时断开连接
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // 监听 chatId 变化，自动订阅新会话
  useEffect(() => {
    if (chatId && wsRef.current?.readyState === WebSocket.OPEN) {
      subscribe(chatId);
    }
  }, [chatId, subscribe]);

  return {
    connect,
    disconnect,
    reconnect,
    sendMessage,
    sendConfig,
    subscribe,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN
  };
}
