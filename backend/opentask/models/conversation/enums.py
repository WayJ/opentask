"""
对话类型枚举

定义所有支持的对话类型。
"""

from enum import Enum


class ConversationType(str, Enum):
    """对话类型枚举"""

    SQL_CHAT = "sql_chat"
    """SQL 对话 - 使用 LangGraph 生成和执行 SQL"""

    DEEP_SEARCH = "deep_search"
    """深度搜索 - 专注于深度信息检索"""

    DATA_ANALYSIS = "data_analysis"
    """数据分析 - 数据分析和可视化"""

    NORMAL_CHAT = "normal_chat"
    """普通对话 - 使用 Agent v3 进行通用对话"""

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: str) -> bool:
        """支持与字符串比较"""
        if isinstance(other, str):
            return self.value.lower() == other.lower()
        return super().__eq__(other)

    @classmethod
    def from_string(cls, value: str) -> "ConversationType":
        """
        从字符串创建枚举值

        Args:
            value: 字符串值

        Returns:
            ConversationType: 对应的枚举值

        Raises:
            ValueError: 如果字符串不匹配任何枚举值
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = [t.value for t in cls]
            raise ValueError(
                f"无效的对话类型: '{value}'. "
                f"支持的类型: {', '.join(valid_values)}"
            )

    @classmethod
    def get_default(cls) -> "ConversationType":
        """获取默认对话类型"""
        return cls.SQL_CHAT

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """
        检查字符串是否为有效的对话类型

        Args:
            value: 待检查的字符串

        Returns:
            bool: 是否有效
        """
        try:
            cls.from_string(value)
            return True
        except ValueError:
            return False

    def requires_connection(self) -> bool:
        """
        检查该对话类型是否需要数据库连接

        Returns:
            bool: 是否需要连接
        """
        return self in {
            ConversationType.SQL_CHAT,
            ConversationType.DATA_ANALYSIS
        }

    def supports_sql_generation(self) -> bool:
        """
        检查该对话类型是否支持 SQL 生成

        Returns:
            bool: 是否支持 SQL 生成
        """
        return self == ConversationType.SQL_CHAT

    def supports_web_search(self) -> bool:
        """
        检查该对话类型是否支持网络搜索

        Returns:
            bool: 是否支持网络搜索
        """
        return self in {
            ConversationType.DEEP_SEARCH,
            ConversationType.NORMAL_CHAT
        }

    def supports_multi_agent(self) -> bool:
        """
        检查该对话类型是否支持多代理协作

        Returns:
            bool: 是否支持多代理
        """
        return self == ConversationType.NORMAL_CHAT

    def get_description(self) -> str:
        """获取对话类型的描述"""
        descriptions = {
            ConversationType.SQL_CHAT: "SQL 对话助手，帮助生成和执行 SQL 查询",
            ConversationType.DEEP_SEARCH: "深度搜索助手，专注于深度信息检索和研究",
            ConversationType.DATA_ANALYSIS: "数据分析助手，提供数据分析和可视化功能",
            ConversationType.NORMAL_CHAT: "智能对话助手，支持多代理协作的通用对话"
        }
        return descriptions.get(self, "未知对话类型")

    def get_display_name(self) -> str:
        """获取对话类型的显示名称"""
        display_names = {
            ConversationType.SQL_CHAT: "SQL 对话",
            ConversationType.DEEP_SEARCH: "深度搜索",
            ConversationType.DATA_ANALYSIS: "数据分析",
            ConversationType.NORMAL_CHAT: "智能对话"
        }
        return display_names.get(self, self.value)
