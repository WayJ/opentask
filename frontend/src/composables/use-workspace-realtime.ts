/**
 * E23：Workspace 业务实时通道（/ws/workspace）
 * 单例：连接、心跳、重连；按 workspace 切换重订。
 */
import { computed, onScopeDispose, ref } from 'vue';
import { getToken } from '@/store/modules/auth/shared';
import { localStg } from '@/utils/storage';

export type WorkspaceRealtimeEventType =
  | 'connected'
  | 'pong'
  | 'issue.created'
  | 'issue.updated'
  | 'issue.deleted'
  | 'inbox.created'
  | 'comment.created'
  | string;

export interface WorkspaceRealtimeEvent {
  type: WorkspaceRealtimeEventType;
  workspace_id?: string;
  ts?: string;
  actor_user_id?: string | null;
  payload?: Record<string, unknown>;
  connection_id?: string;
}

type Listener = (event: WorkspaceRealtimeEvent) => void;

const connected = ref(false);
const lastError = ref<string | null>(null);
const lastEvent = ref<WorkspaceRealtimeEvent | null>(null);
const listeners = new Set<Listener>();

let socket: WebSocket | null = null;
let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let manualClose = false;
let reconnectAttempt = 0;
let started = false;
let workspaceWatchStop: (() => void) | null = null;

function buildWsUrl(workspaceId: string, token: string): string {
  // 直连后端（不经 vite HTTP proxy rewrite）；CORS/WS 同源策略对 WS 握手按 URL 目标处理
  const base = import.meta.env.VITE_SERVICE_BASE_URL || 'http://localhost:7377';
  const u = new URL(base, typeof window !== 'undefined' ? window.location.origin : 'http://localhost');
  const proto = u.protocol === 'https:' ? 'wss:' : 'ws:';
  const qs = new URLSearchParams({ token, workspace_id: workspaceId });
  return `${proto}//${u.host}/ws/workspace?${qs.toString()}`;
}

function clearHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function clearReconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function emit(event: WorkspaceRealtimeEvent) {
  lastEvent.value = event;
  listeners.forEach(fn => {
    try {
      fn(event);
    } catch {
      /* ignore listener errors */
    }
  });
}

function scheduleReconnect() {
  clearReconnect();
  const delay = Math.min(1000 * 2 ** reconnectAttempt, 15000);
  reconnectAttempt += 1;
  reconnectTimer = setTimeout(() => {
    connect();
  }, delay);
}

function connect() {
  const token = getToken();
  const workspaceId = localStg.get('workspaceId') || '';
  if (!token || !workspaceId) {
    disconnect(false);
    return;
  }

  manualClose = false;
  clearReconnect();
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    // 若 workspace 变化需要重连
    disconnect(false);
  }

  let url: string;
  try {
    url = buildWsUrl(workspaceId, token);
  } catch (e) {
    lastError.value = String(e);
    return;
  }

  try {
    socket = new WebSocket(url);
  } catch (e) {
    lastError.value = String(e);
    scheduleReconnect();
    return;
  }

  socket.onopen = () => {
    connected.value = true;
    lastError.value = null;
    reconnectAttempt = 0;
    clearHeartbeat();
    heartbeatTimer = setInterval(() => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'ping' }));
      }
    }, 25000);
  };

  socket.onmessage = ev => {
    try {
      const data = JSON.parse(String(ev.data)) as WorkspaceRealtimeEvent;
      if (data.type === 'pong') return;
      emit(data);
    } catch {
      /* ignore malformed */
    }
  };

  socket.onerror = () => {
    lastError.value = 'workspace realtime error';
  };

  socket.onclose = () => {
    connected.value = false;
    clearHeartbeat();
    socket = null;
    if (!manualClose) {
      scheduleReconnect();
    }
  };
}

function disconnect(manual = true) {
  manualClose = manual;
  clearHeartbeat();
  clearReconnect();
  if (socket) {
    try {
      socket.close();
    } catch {
      /* ignore */
    }
    socket = null;
  }
  connected.value = false;
}

function startRealtime() {
  if (started) return;
  started = true;
  connect();
  // 轮询 localStorage workspace 变化（Switcher 写入）
  let lastWs = localStg.get('workspaceId') || '';
  const iv = setInterval(() => {
    const cur = localStg.get('workspaceId') || '';
    if (cur !== lastWs) {
      lastWs = cur;
      connect();
    }
    const tok = getToken();
    if (!tok && connected.value) {
      disconnect(true);
    } else if (tok && !socket && !manualClose) {
      connect();
    }
  }, 1500);
  workspaceWatchStop = () => clearInterval(iv);
}

function stopRealtime() {
  workspaceWatchStop?.();
  workspaceWatchStop = null;
  disconnect(true);
  started = false;
}

export function subscribeWorkspaceRealtime(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** 防抖工具（列表 refetch） */
export function debounceFn<T extends (...args: any[]) => void>(fn: T, ms: number): T {
  let t: ReturnType<typeof setTimeout> | null = null;
  const wrapped = ((...args: any[]) => {
    if (t) clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  }) as T;
  return wrapped;
}

export function useWorkspaceRealtime() {
  startRealtime();

  onScopeDispose(() => {
    // 多处挂载时不立刻停；仅去掉本 scope 无额外状态
  });

  return {
    connected: computed(() => connected.value),
    lastError: computed(() => lastError.value),
    lastEvent: computed(() => lastEvent.value),
    subscribe: subscribeWorkspaceRealtime,
    reconnect: () => connect(),
    disconnect: () => disconnect(true)
  };
}

/** 测试辅助 */
export function resetWorkspaceRealtimeForTests() {
  stopRealtime();
  listeners.clear();
  lastEvent.value = null;
  lastError.value = null;
  reconnectAttempt = 0;
}

export function testBuildWsUrl(workspaceId: string, token: string) {
  return buildWsUrl(workspaceId, token);
}
