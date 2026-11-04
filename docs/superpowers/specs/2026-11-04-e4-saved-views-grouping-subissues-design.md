# E4 设计：Saved Views · 列表分组 · 一等公民子 Issue

日期：2026-11-04  
Epic：E4  
状态：active（S3 实现中；S1/S2 closed）

## 1. 目标

对齐 Linear 手感，交付：

1. **S1** 个人 Saved Views（收藏/保存筛选与排序）
2. **S2** Issue 列表按属性分组泳道
3. **S3** 一等公民父子子 Issue（`parent_issue_id`）

不做：⌘K、Cycles、Labels 打磨、工作区共享视图、邮件/IM、远程推送。

## 2. S1 — Saved Views（详）

### 2.1 数据模型 `IssueSavedView` / 表 `issue_saved_views`

| 列 | 类型 | 说明 |
|---|---|---|
| id | String(36) PK | uuid |
| workspace_id | String(36) FK → workspaces | 租户 |
| owner_user_id | String(36) | 个人归属；列表恒按当前用户过滤 |
| name | String(128) | 显示名 |
| is_favorite | Boolean | 收藏星标 |
| filter_json | JSON | 筛选配置 |
| sort_json | JSON | `{sort_by, sort_order}` |
| display_json | JSON nullable | 预留：`view_mode` / `group_by`（S2） |
| created_at / updated_at | DateTime | |

索引建议：`(workspace_id, owner_user_id)`、`(owner_user_id, is_favorite)`。

**禁止**复用 `IssueCollection`（那是 issue_id 袋子，不是筛选配置）。

### 2.2 `filter_json` 形状

与前端 `ParsedQuery` / 后端 `IssueQueryParams` 对齐（字段均可选）：

```json
{
  "status": "open",
  "type": "bug",
  "priority": "high",
  "project_id": "...",
  "assignee_id": "...",
  "reporter_id": "...",
  "search": "关键词或智能搜索残片",
  "tab": "open"
}
```

`sort_json`：

```json
{ "sort_by": "created_at", "sort_order": "desc" }
```

`display_json`（S1 可空；S2 用）：

```json
{ "view_mode": "list", "group_by": "priority" }
```

### 2.3 API `/api/saved-views`

鉴权：`authenticate` + **必填** `X-Workspace-Id` + `WorkspaceService.require_member`。  
所有读写额外约束 `owner_user_id == current_user.id`（非 owner → 404，不泄漏存在性）。

信封：`success_response`（与 Inbox 一致）。

| Method | Path | Body / 行为 |
|---|---|---|
| GET | `` | 列出我在当前工作区的视图（收藏优先可选） |
| POST | `` | `{name, filter, sort?, is_favorite?, display?}` 创建 |
| GET | `/{id}` | 取一条（非 owner → 404） |
| PATCH | `/{id}` | 更新 name / filter / sort / is_favorite / display |
| DELETE | `/{id}` | 删除 |
| POST | `/{id}/favorite`（可选） | `{is_favorite: bool}` 或 toggle |

序列化建议 camelCase：`workspaceId`, `ownerUserId`, `isFavorite`, `filter`, `sort`, `display`, `createdAt`, `updatedAt`。

### 2.4 前端（Issue 列表）

文件：`frontend/src/views/issue/list/index.vue` + `frontend/src/service/api/saved-views.ts`

- 工具栏：**保存当前视图**（Modal 输入名称 → POST，payload = 当前 `filters` + smartSearch 解析字段 + tab + 可选 sort）
- **我的视图**下拉：GET list；点击应用 → 写回 `filters` / `smartSearchValue` / tab → `loadIssues`
- 星标：PATCH / favorite；列表中收藏置顶或标星
- Naive UI / DESIGN.md 令牌；无新色板

### 2.5 测试

`backend/tests/api/test_saved_views.py`：

- create + list
- 用户 B 看不到用户 A（同工作区成员亦不可见他人个人视图）
- update / delete
- 缺 `X-Workspace-Id` → 400；非成员 → 403
- favorite 切换

## 3. S2 — 列表分组泳道

- UI：列表工具栏「分组」选择：`none` / `status` / `assignee` / `priority` / `type`
- **客户端**对当前 `filteredIssues` 分桶（`groupIssuesBy`）；分组开启时列表展示全量筛选结果（不分页）
- 选择写入 Saved View `display_json.group_by`；无活动视图则仅本地状态
- 列表泳道 **展示-only**：跨泳道拖拽改字段不在范围；看板 status 拖拽保持 IssueBoard 既有行为
- 不做共享视图、不做复杂自定义字段分组、不做 S3 `parent_issue_id`

## 4. S3 — 一等公民子 Issue

- Issue 增加可空 `parent_issue_id` FK → `issues.id`（同 workspace；服务层强制）
- 拒：自指、父不存在、跨工作区、环（祖先链含自身）
- API：
  - Create/Update 接受 `parent_issue_id`（`null` 清空）
  - List/Get 恒含 `parent_issue_id`
  - Get 另含 `children` 轻量摘要 `{id, issue_code, title, status}`；另 `GET /api/issues/{id}/children`
- UI：详情显示父链接 + 子列表 + 添加子 Issue；列表对当前筛选结果 **depth-1** 客户端嵌套缩进（父不在结果集则子顶层展示）
- **不用** `IssueRelation` 表达父子（Relation 保留 blocks/related 等）
- Alembic 接在 saved_views `d0e1f2a3b4c5` 之后

## 5. 风险与约束

- 个人隔离必须有负例测试
- JSON 列用 SQLAlchemy `JSON`（与 Task/Issue 一致），测试库 `create_all`
- Alembic 迁移接在 inbox `c9d8e7f6a5b4` 之后
- 本地 worktree；不推远程

## 6. 文件路径（S1）

| 层 | 路径 |
|---|---|
| Model | `backend/opentask/models/issue_saved_view/` |
| Migration | `backend/alembic/versions/2026_11_04_0100-d0e1f2a3b4c5_issue_saved_views.py` |
| Service | `backend/opentask/services/saved_view/service.py` |
| Router | `backend/opentask/api/saved_views/router.py` |
| App mount | `backend/opentask/app.py` |
| Tests | `backend/tests/api/test_saved_views.py` |
| FE API | `frontend/src/service/api/saved-views.ts` |
| FE UI | `frontend/src/views/issue/list/index.vue` |
