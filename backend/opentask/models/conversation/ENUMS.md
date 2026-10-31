# ConversationType 枚举使用指南

## 概述

`ConversationType` 是一个枚举类型，用于类型安全地表示对话类型。

## 枚举值

```python
from opentask.models.conversation.enums import ConversationType

class ConversationType(str, Enum):
    SQL_CHAT = "sql_chat"        # SQL 对话
    DEEP_SEARCH = "deep_search"  # 深度搜索
    DATA_ANALYSIS = "data_analysis"  # 数据分析
    NORMAL_CHAT = "normal_chat"  # 普通对话 (Agent v3)
```

## 基本用法

### 创建枚举实例

```python
# 方式 1: 从枚举直接获取
chat_type = ConversationType.NORMAL_CHAT

# 方式 2: 从字符串创建
chat_type = ConversationType.from_string("normal_chat")

# 方式 3: 获取默认类型
default_type = ConversationType.get_default()  # SQL_CHAT
```

### 比较操作

```python
# 与枚举比较
if conversation_type == ConversationType.NORMAL_CHAT:
    print("这是普通对话")

# 与字符串比较（自动处理大小写）
if conversation_type == "normal_chat":
    print("这也是普通对话")
```

### 实用方法

```python
# 检查字符串是否有效
is_valid = ConversationType.is_valid("normal_chat")  # True
is_valid = ConversationType.is_valid("invalid")  # False

# 获取描述
description = ConversationType.NORMAL_CHAT.get_description()
# "智能对话助手，支持多代理协作的通用对话"

# 获取显示名称
display_name = ConversationType.NORMAL_CHAT.get_display_name()
# "智能对话"

# 检查特性
requires_connection = ConversationType.SQL_CHAT.requires_connection()  # True
supports_sql = ConversationType.SQL_CHAT.supports_sql_generation()  # True
supports_search = ConversationType.NORMAL_CHAT.supports_web_search()  # True
supports_multi_agent = ConversationType.NORMAL_CHAT.supports_multi_agent()  # True
```

## 在 API 中使用

### 创建对话

```python
POST /api/conversations
{
    "name": "我的对话",
    "conversation_type": "chat"  # 字符串形式
}
```

### Pydantic 模型

```python
from opentask.models.conversation.schema import CreateConversationIn

# 自动转换为枚举
data = CreateConversationIn(
    name="我的对话",
    conversation_type="normal_chat"  # 字符串 -> ConversationType.NORMAL_CHAT
)

# 使用枚举
data = CreateConversationIn(
    name="我的对话",
    conversation_type=ConversationType.NORMAL_CHAT
)
```

### 响应

```python
{
    "id": "uuid",
    "name": "我的对话",
    "conversation_type": "normal_chat",  # 字符串形式
    ...
}
```

## 数据库存储

虽然我们使用枚举进行类型安全，但数据库中仍然存储为字符串：

```python
class ConversationModel(DBModel):
    conversation_type: Mapped[str]  # 存储为 "chat", "sql_chat" 等

    def get_conversation_type_enum(self) -> ConversationType:
        """转换为枚举"""
        return ConversationType.from_string(self.conversation_type)
```

## 在服务中使用

### 路由逻辑

```python
from opentask.models.conversation.enums import ConversationType

async def query(conversation_id: UUID, query: str):
    conversation = await get_conversation(conversation_id)

    # 使用枚举比较
    if conversation.conversation_type == ConversationType.NORMAL_CHAT:
        # 使用 Agent v3
        return await agent_v3_service.query(...)
    elif conversation.conversation_type == ConversationType.SQL_CHAT:
        # 使用 LangGraph
        return await langgraph_service.query(...)
```

### 类型检查

```python
def handle_conversation(type: ConversationType):
    # IDE 可以提供自动补全
    if type == ConversationType.NORMAL_CHAT:
        print("处理普通对话")
    elif type == ConversationType.SQL_CHAT:
        print("处理 SQL 对话")
    # ...
```

## 特性对比表

| 对话类型 | 显示名称 | 需要数据库 | SQL 生成 | 网络搜索 | 多代理 |
|---------|---------|-----------|---------|---------|--------|
| `SQL_CHAT` | SQL 对话 | ✅ | ✅ | ❌ | ❌ |
| `DEEP_SEARCH` | 深度搜索 | ❌ | ❌ | ✅ | ❌ |
| `DATA_ANALYSIS` | 数据分析 | ✅ | ❌ | ❌ | ❌ |
| `NORMAL_CHAT` | 智能对话 | ❌ | ❌ | ✅ | ✅ |

## 错误处理

```python
try:
    type = ConversationType.from_string("invalid")
except ValueError as e:
    print(e)
    # "无效的对话类型: 'invalid'. 支持的类型: sql_chat, deep_search, data_analysis, normal_chat"
```

## 最佳实践

1. **使用枚举而不是字符串**
   ```python
   # 推荐
   if conv_type == ConversationType.NORMAL_CHAT:
       ...

   # 不推荐
   if conv_type == "normal_chat":
       ...
   ```

2. **利用类型检查**
   ```python
   def process_chat(conversation_type: ConversationType):
       if conversation_type.supports_multi_agent():
           # IDE 知道这里的类型
           ...
   ```

3. **错误处理**
   ```python
   if not ConversationType.is_valid(user_input):
       raise ValueError(f"不支持的对话类型: {user_input}")
   ```

## 扩展新类型

如果需要添加新的对话类型：

1. 在 `ConversationType` 枚举中添加新值
2. 更新 `get_description()` 和 `get_display_name()` 方法
3. 更新特性方法（如 `requires_connection()`）
4. 在 `ConversationService` 中添加对应的处理逻辑

示例：

```python
class ConversationType(str, Enum):
    # ... 现有值

    CODE_ASSISTANT = "code_assistant"  # 新增示例

    def get_description(self) -> str:
        descriptions = {
            # ... 现有描述
            ConversationType.CODE_ASSISTANT: "编程助手，提供代码编写和调试功能"
        }
        return descriptions.get(self, "未知对话类型")
```

## 总结

使用 `ConversationType` 枚举可以：

✅ 提供类型安全
✅ 避免字符串拼写错误
✅ 便于 IDE 自动补全和重构
✅ 集中管理所有对话类型
✅ 提供丰富的实用方法
✅ 保持与数据库的兼容性（仍存储为字符串）
