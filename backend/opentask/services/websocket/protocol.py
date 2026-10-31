"""
WebSocket Hub - 协议处理

负责消息的解析、验证和响应
"""

import json
import logging
from typing import Optional, Tuple, Any

logger = logging.getLogger(__name__)


class ProtocolHandler:
    """协议处理器"""

    # 消息类型常量
    TYPE_TASK_SUBMIT = "task:submit"
    TYPE_TASK_PROGRESS = "task:progress"
    TYPE_TASK_COMPLETE = "task:complete"
    TYPE_TASK_FAIL = "task:fail"
    TYPE_TASK_CANCEL = "task:cancel"
    TYPE_TASK_PAUSE = "task:pause"
    TYPE_TASK_RESUME = "task:resume"
    TYPE_TASK_QUERY = "task:query"
    TYPE_TASK_RESPONSE = "task:response"
    TYPE_AGENT_REGISTER = "agent:register"
    TYPE_AGENT_HEARTBEAT = "agent:heartbeat"
    TYPE_AGENT_STATUS = "agent:status"
    TYPE_SYSTEM_ACK = "system:ack"
    TYPE_SYSTEM_ERROR = "system:error"
    TYPE_SYSTEM_CONFIG = "system:config"

    def __init__(self):
        pass

    def parse_message(self, raw_message: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        解析原始消息

        Args:
            raw_message: 原始 JSON 字符串

        Returns:
            (解析后的消息, 错误消息)
        """
        try:
            message = json.loads(raw_message)
            if not isinstance(message, dict):
                return None, "Message must be an object"
            return message, None
        except json.JSONDecodeError as e:
            return None, f"Invalid JSON: {str(e)}"

    def validate_message(self, message: dict) -> Tuple[bool, Optional[str]]:
        """
        验证消息格式

        Args:
            message: 消息对象

        Returns:
            (是否有效, 错误消息)
        """
        required_fields = ["id", "type", "sender", "recipient", "timestamp", "payload"]

        for field in required_fields:
            if field not in message:
                return False, f"Missing required field: {field}"

        # 验证 payload
        if not isinstance(message["payload"], dict):
            return False, "Payload must be an object"

        return True, None

    def create_ack(self, original_id: str, status: str = "received",
                   message: Optional[str] = None) -> dict:
        """创建确认消息"""
        return {
            "id": self._generate_id(),
            "type": self.TYPE_SYSTEM_ACK,
            "sender": "hub",
            "recipient": "sender",
            "timestamp": self._timestamp(),
            "payload": {
                "originalId": original_id,
                "status": status,
                "message": message,
            },
            "version": "1.0"
        }

    def create_error(self, code: str, error_message: str,
                    original_id: Optional[str] = None) -> dict:
        """创建错误消息"""
        payload = {
            "code": code,
            "message": error_message,
        }
        if original_id:
            payload["originalId"] = original_id

        return {
            "id": self._generate_id(),
            "type": self.TYPE_SYSTEM_ERROR,
            "sender": "hub",
            "recipient": "sender",
            "timestamp": self._timestamp(),
            "payload": payload,
            "version": "1.0"
        }

    def is_task_message(self, message_type: str) -> bool:
        """判断是否是任务相关消息"""
        return message_type.startswith("task:")

    def is_agent_message(self, message_type: str) -> bool:
        """判断是否是 Agent 相关消息"""
        return message_type.startswith("agent:")

    def is_system_message(self, message_type: str) -> bool:
        """判断是否是系统消息"""
        return message_type.startswith("system:")

    def extract_task_id(self, message: dict) -> Optional[str]:
        """从消息中提取任务 ID"""
        payload = message.get("payload", {})
        return payload.get("taskId") or payload.get("task_id")

    def extract_agent_id(self, sender: str) -> Optional[str]:
        """从发送方标识中提取 Agent ID"""
        if sender.startswith("agent:"):
            return sender[6:]
        return None

    def wrap_for_broadcast(self, message: dict, original_sender: str) -> dict:
        """为广播包装消息"""
        # 在某些情况下需要修改 recipient 为 broadcast
        wrapped = message.copy()
        if wrapped.get("recipient") != "broadcast":
            # 保持原始 recipient，但在某些场景下需要特殊处理
            pass
        return wrapped

    def _generate_id(self) -> str:
        """生成消息 ID"""
        import time
        import random
        return f"msg_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

    def _timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


class LegacyProtocolHandler:
    """旧版协议处理器 - 用于兼容现有 Hub"""

    # 旧版消息类型映射到新版
    TYPE_MAP = {
        "task_assignment": "task:submit",
        "task_progress": "task:progress",
        "task_completion": "task:complete",
        "task_control": "task:cancel",
        "task_query": "task:query",
        "task_query_response": "task:response",
    }

    def convert_to_new(self, legacy_message: dict) -> Optional[dict]:
        """
        将旧版消息转换为新版格式

        Args:
            legacy_message: 旧版消息

        Returns:
            新版格式消息，如果转换失败返回 None
        """
        try:
            msg_type = legacy_message.get("type")
            if not msg_type or msg_type not in self.TYPE_MAP:
                return None

            new_type = self.TYPE_MAP[msg_type]
            source = legacy_message.get("source", "")
            data = legacy_message.get("data", {})

            # 基本转换
            new_message = {
                "id": self._generate_id(),
                "type": new_type,
                "sender": source,
                "recipient": "backend" if source == "opentask" else "frontend",
                "timestamp": legacy_message.get("timestamp", self._timestamp()),
                "payload": self._convert_payload(new_type, data),
                "version": "1.0"
            }

            return new_message

        except Exception as e:
            logger.error(f"Error converting legacy message: {e}")
            return None

    def _convert_payload(self, new_type: str, data: dict) -> dict:
        """转换 payload 格式"""
        # 字段名转换 (snake_case -> camelCase)
        converted = {}
        for key, value in data.items():
            if key == "task_id":
                converted["taskId"] = value
            elif key == "progress_percentage":
                converted["progress"] = value
            elif key == "current_step":
                converted["currentStep"] = value
            elif key == "result_summary":
                converted["summary"] = value
            elif key == "estimated_completion":
                converted["estimatedCompletion"] = value
            elif key == "retry_possible":
                converted["retryable"] = value
            else:
                converted[key] = value

        return converted

    def _generate_id(self) -> str:
        import time
        import random
        return f"msg_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

    def _timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
