# 数据库迁移文件整理记录

## 整理日期（第二次）：2026-10-31

## PG 基线重建（ADR D11）

- 决策：dev/test/prod 统一切换 PostgreSQL（无生产 MySQL 数据需迁移），旧 MySQL 方言迁移链无保留价值。
- 删除 `alembic/versions/` 下全部 MySQL 方言迁移文件（2026-02 至 2026-10 共 47 个），由单一基线迁移 `003ccd38d5cd_pg_initial_baseline` 取代，覆盖当前全部 45 张表与 20 个原生枚举类型。
- `downgrade()` 已显式回收原生枚举类型（drop_table 不回收内联创建的 ENUM 类型，否则降级后再 upgrade 报 DuplicateObject）。
- 全新库执行 `alembic upgrade head` 即可完成初始化；升级/降级往返已在 postgres:16 容器验证。

---

## 整理日期（第一次）：2026-02-23

## 整理原因
- 项目是从其他项目迁移过来的，包含大量不必要的迁移文件
- 需要创建一个干净的初始迁移，包含项目实际需要的所有表
- 简化迁移历史，便于后续维护

## 删除的迁移文件

以下迁移文件已被删除（原文件已备份到 `alembic/versions_backup/` 目录）：

### 基础表迁移
1. **2024_05_28_2128-1fcab2512ee2_initial_migration_not.py**
   - 原始迁移文件，创建基础表（connections, user, conversations, messages, results, media）
   - 删除原因：被新的初始迁移替代

2. **2024_07_11_2328-4e70c3318aaa_added_connection_type.py**
   - 为 connections 表添加 type 字段
   - 删除原因：已合并到新的初始迁移

3. **2024_08_07_1129-3f6e32040035_add_openai_base_url_column_to_user_table.py**
   - 为 user 表添加 openai_base_url 字段
   - 删除原因：已合并到新的初始迁移

4. **2024_08_15_1302-fa9cefccac47_add_connection_options_column_json.py**
   - 为 connections 表添加 options 字段（JSON 类型）
   - 删除原因：已合并到新的初始迁移

5. **2024_09_21_2321-3d35dcd30116_added_user_analytics.py**
   - 为 user 表添加 analytics_enabled 字段
   - 删除原因：已合并到新的初始迁移

6. **2025_05_19_0834-ca20728c080d_add_hide_sql_user_setting.py**
   - 为 user 表添加 hide_sql_preference 字段
   - 删除原因：已合并到新的初始迁移

### 对话功能迁移
7. **2025_10_28_1155-9epwsql0r9ay_add_ai_analysis_conversation_fields.py**
   - 为 conversations 表添加 conversation_type、workspace_id、ai_settings 字段
   - 删除原因：已合并到新的初始迁移

8. **2025_10_29_1337-f8k9m7l2j3a1_make_connection_id_optional.py**
   - 修改 conversations.connection_id 为可空
   - 删除原因：此功能在当前模型中不需要，connection_id 保持为非空

### DataInsight 模块迁移
9. **2025_01_09_1200-add_datainsight_models.py**
   - 创建 DataInsight 相关的 8 个表（datainsight_sessions, analysis_requests, analysis_executions 等）
   - 删除原因：DataInsight 模块不是当前项目的核心功能，暂时不需要

### 修复迁移
10. **fix_id_field_length.py**
    - 修复 ID 字段长度（仅适用于 SQLite）
    - 删除原因：项目使用 PostgreSQL，不需要此迁移

11. **fix_uuid_fields.py**
    - 修复 UUID 字段类型（仅适用于 SQLite）
    - 删除原因：项目使用 PostgreSQL，不需要此迁移

### 用户管理迁移
12. **2025_10_28_1916-hk2hbngcjqnx_add_default_admin_user.py**
    - 为 user 表添加 password 字段，并创建默认管理员用户
    - 删除原因：已合并到新的初始迁移

### 需求管理迁移
13. **2026_02_23_1200-add_requirement_management_tables.py**
    - 创建需求管理相关的 7 个表（projects, repo_configs, requirements, events 等）
    - 删除原因：已合并到新的初始迁移

## 新创建的迁移文件

### 2026_02_23_1200-initial_migration.py
这是新的初始迁移文件，包含项目实际需要的所有 13 个核心表：

1. **user** - 用户表
   - 包含所有必要字段：name, password, openai_api_key, preferred_openai_model 等
   - 包含分析相关设置：analytics_enabled, hide_sql_preference
   - 包含 Sentry 开关：sentry_enabled

2. **connections** - 数据库连接表
   - 完整的数据库连接配置
   - 包含 type 和 options 字段

3. **conversations** - 对话表
   - 包含对话类型、工作区 ID、AI 设置等字段
   - 与 connections 表关联

4. **messages** - 消息表
   - 存储对话消息内容
   - 与 conversations 表关联

5. **results** - 结果表
   - 存储 AI 执行结果
   - 与 messages 表关联

6. **media** - 媒体表
   - 存储二进制媒体数据

7. **projects** - 项目表
   - 项目基本信息管理

8. **repo_configs** - 仓库配置表
   - Git 仓库配置信息
   - 与 projects 表关联

9. **requirements** - 需求表
   - 需求/问题追踪
   - 包含状态、优先级、标签等字段

10. **events** - 事件表（事件溯源）
    - 记录需求生命周期中的所有事件
    - 与 requirements 表关联

11. **requirement_repos** - 需求-仓库关联表
    - 多对多关联关系
    - 支持分支、PR URL、合并状态等

12. **comments** - 评论表
    - 需求评论功能
    - 与 requirements 表关联

13. **queue_jobs** - 队列任务表
    - 后台任务执行记录
    - 支持重试机制

## 数据模型对应关系

所有表都对应项目中的 SQLAlchemy 模型：

| 表名 | 模型类 | 文件路径 |
|-----|--------|---------|
| user | UserModel | opentask/models/user/model.py |
| connections | ConnectionModel | opentask/models/connection/model.py |
| conversations | ConversationModel | opentask/models/conversation/model.py |
| messages | MessageModel | opentask/models/message/model.py |
| results | ResultModel | opentask/models/result/model.py |
| media | MediaModel | opentask/models/media/model.py |
| projects | Project | opentask/models/requirement/model.py |
| repo_configs | RepoConfig | opentask/models/requirement/model.py |
| requirements | Requirement | opentask/models/requirement/model.py |
| events | Event | opentask/models/requirement/model.py |
| requirement_repos | RequirementRepo | opentask/models/requirement/model.py |
| comments | Comment | opentask/models/requirement/model.py |
| queue_jobs | QueueJob | opentask/models/requirement/model.py |

## 迁移依赖关系

新的初始迁移没有依赖（down_revision = None），这表示它是一个全新的起点。

## 注意事项

1. **数据库类型**：项目使用 PostgreSQL，所有迁移都针对 PostgreSQL 优化
2. **UUID 类型**：使用 PostgreSQL 的原生 UUID 类型
3. **JSON 类型**：使用 PostgreSQL 的 JSONB 类型
4. **级联删除**：合理设置外键的 ON DELETE CASCADE
5. **索引优化**：为常用查询字段创建索引

## 如何使用

1. **首次部署**：
   ```bash
   cd backend
   uv run alembic upgrade head
   ```

2. **查看当前版本**：
   ```bash
   uv run alembic current
   ```

3. **查看迁移历史**：
   ```bash
   uv run alembic history
   ```

## 备份文件位置

所有被删除的迁移文件已备份到：
```
/workspace/opentask/backend/alembic/versions_backup/
```

如果需要恢复旧迁移，可以从该目录复制回 `alembic/versions/` 目录。

## 后续迁移规则

创建新迁移时，请遵循以下规则：

1. 每个功能一个迁移文件
2. 迁移文件名格式：`YYYY_MM_DD_HHMM-revision_slug.py`
3. 确保设置正确的 down_revision
4. 同时编写 upgrade 和 downgrade 函数
5. 测试迁移的升级和降级

## 整理后的迁移列表

- **2026_02_23_1200-initial_migration.py** - 初始迁移（包含所有核心表）

未来新增的迁移将依赖这个初始迁移。
