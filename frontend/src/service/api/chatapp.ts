/**
 * ChatApp API 服务
 *
 * 用于调用 ChatApp 后端的 REST API
 * 自动携带 OpenTask 的认证 token
 */

import { chatappRequest } from '@/service/request/chatapp';

export interface Chat {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChatMessage {
  id: string;
  chatId: string;
  role: 'user' | 'assistant' | 'system' | 'tool_use' | 'tool_result';
  content: string;
  timestamp: string;
  toolName?: string;
  toolInput?: any;
  toolUseId?: string;
  isError?: boolean;
}

/**
 * 获取当前用户的所有聊天会话
 */
export async function fetchChats(): Promise<Chat[]> {
  return chatappRequest.get('/api/chats');
}

/**
 * 创建新的聊天会话
 */
export async function createChat(title?: string): Promise<Chat> {
  return chatappRequest.post('/api/chats', { title });
}

/**
 * 获取指定聊天会话的详情
 */
export async function fetchChat(id: string): Promise<Chat> {
  return chatappRequest.get(`/api/chats/${id}`);
}

/**
 * 更新聊天会话标题
 */
export async function updateChatTitle(id: string, title: string): Promise<Chat> {
  return chatappRequest.patch(`/api/chats/${id}`, { title });
}

/**
 * 删除聊天会话
 */
export async function deleteChat(id: string): Promise<{ success: boolean }> {
  return chatappRequest.delete(`/api/chats/${id}`);
}

/**
 * 获取聊天会话的所有消息
 */
export async function fetchChatMessages(chatId: string): Promise<ChatMessage[]> {
  return chatappRequest.get(`/api/chats/${chatId}/messages`);
}

/**
 * 获取聊天会话的完整信息（包括消息）
 */
export async function fetchChatWithMessages(id: string): Promise<{ chat: Chat; messages: ChatMessage[] }> {
  return chatappRequest.get(`/api/chats/${id}/full`);
}

/**
 * 配置 CLI 凭证
 */
export interface CliConfig {
  apiUrl: string;
  token: string;
}

/**
 * 保存 CLI 凭证配置
 * 通过 WebSocket 发送，不需要专门的 REST API
 */
export interface CliConfigMessage {
  type: 'config';
  chatId: string;
  apiUrl: string;
  token: string;
}
