# E7 设计：Labels 打磨 · Shared Views · Display · Board Swimlanes

日期：2026-11-04  
Epic：E7  
状态：design（Phase 1；产品实现未开工）  
基线：`sprint/E6-S3` @ `7dd7c55`；worktree `/workspace/opentask-worktrees/E7-S1`（分支 `sprint/E7-S1`）  
北星：OpenTask Linear PRD §E7

## 1. 目标

对齐 Linear，交付厚 Epic：

1. **S1** Labels：workspace 作用域 + 颜色/分组 + CRUD + Issue 打标恢复 + 列表 `groupBy: label` + 热键 **L** / picker + ⌘K 最小标签动作
2. **S2** Shared Saved Views：`is_shared` + 个人/共享隔离列表 + 权限（member+ 建；creator+owner 写；Save As）
3. **S3** Display options（字段显隐 + 个人默认）+ Board 行维泳道（+ hide empty）+ Epic local-complete

不做：标签退休治理、Insights、强制唯一工作区默认布局、跨泳道拖拽改字段、远程推送、E8+。

## 2. 探索事实（Phase 1 inventory）

### 2.1 Tags / Labels（半废弃）

| 资产 | 路径 | 现状 |
|---|---|---|
| `Tag` 模型 | `backend/opentask/models/tag/model.py` | `id` int PK、`name` **全局 unique**、`created_at`；**无** `color` / `group` / `workspace_id` |
| DB 基线 | Alembic `003ccd38d5cd` | `tags(name unique)`；`issue_tags(issue_id, tag_id)` |
| `IssueTag` | `models/issue/model.py` | 关联可用；`tag` relationship 注释为已移除 |
| Issue API | `api/issue/router.py` | `GET /{id}/tags` **硬编码空列表**；POST/DELETE 仍调 `IssueService.add_tag/remove_tag` |
| 契约层 | `api/tasks/service.py` | `get_or_create_tag` / `sync_issue_labels` 按 **全局 name** 工作（Jira labels） |
| Schema 遗物 | `schemas/tag.py` | 声明 `color`，但模型无列；文件标注知识库 Tag 已移除 |
| FE | `service/api/tag.ts` | 标废弃，仍指向 `/api/tags*` |
| FE 详情 | `views/issue/detail/index.vue` | 有 tags UI，依赖 GET tags（现恒空） |
| **Router** | `app.py` | **无** `/api/tags` 注册 |

结论：产品「Labels」能力碎片化；E7 必须 workspace 化并恢复一等公民 CRUD，同时兼容 Jira sync。

### 2.2 Saved Views（E4 个人 only）

路径：`models/issue_saved_view/model.py` · `services/saved_view/service.py` · `api/saved_views/router.py`

| 字段/行为 | 现状 |
|---|---|
| `owner_user_id` | 强制；`list_mine` / `get_mine` 按当前用户 |
| `is_shared` / visibility | **不存在** |
| `filter_json` / `sort_json` | 有 |
| `display_json` | 有；FE 现写 `{ view_mode, group_by }` |
| 权限 | 非 owner → 404；无「共享可读」路径 |
| Save As | **无** |

### 2.3 列表 groupBy + Board

| 资产 | 现状 | E7 缺口 |
|---|---|---|
| `GroupByKey` | `'none'\|'status'\|'assignee'\|'priority'\|'type'` | 无 `label` |
| `groupIssuesBy.ts` | 客户端分桶；列表展示-only | 需多标签展开策略 |
| `IssueListGrouped.vue` | 消费 buckets | 可复用 |
| `IssueBoard.vue` | **仅** status 列；卡片硬编码 code/priority/title/assignee | 无行维泳道；无字段显隐 |
| Saved View apply | `apply-saved-view.ts` 恢复 `group_by` | 需认 `label` + 新 display 键 |

### 2.4 E5 焦点 / 热键扩展点

| 资产 | 扩展方式 |
|---|---|
| `resolveIssueHotkeyAction` | 加 `key === 'l'` → `{ type: 'labels' }`（需 `hasFocusedIssue`） |
| `IssueFieldPickerKind` | 加 `'labels'` |
| `issue-hotkey-picker-host.vue` | 新面板：多选 toggle 标签 / 搜索创建 |
| `useAppHotkeys` | `case 'labels': pickers.openLabels()` |
| `useIssueFocus` | 已有；L 依赖焦点 |
| ⌘K | 可选静态 action「Add label…」+ 实体/命令搜标签名（S1 最小：焦点动作即可；面板命令可同 Sprint） |

### 2.5 display_json 今日用法

```json
{ "view_mode": "list" | "board", "group_by": "none" | "status" | "assignee" | "priority" | "type" }
```

无 `fields`、无 `swimlane_by`、无个人 prefs 表、无 localStorage display 键。

### 2.6 Alembic head

当前 tip head：`a1b2c3d4e5f7`（`issues.cycle_id` + `estimate_points`）。  
E7-S1 新 revision：`down_revision = a1b2c3d4e5f7`。

### 2.7 角色

`WorkspaceMember.role` ∈ `owner|member|viewer`。写业务 = member+；设置类 owner。共享 View：见 §5。

## 3. 架构总览

```
Workspace
  ├── tag_groups[]
  ├── tags[]  (color, group_id, workspace_id)
  │      ↑ issue_tags
  │    Issue[]
  ├── issue_saved_views[]  (owner_user_id, is_shared)
  └── issue_display_prefs[] (per user personal display default)

API /api/tags (+ /api/tag-groups) ── TagService
API /api/saved-views ── SavedViewService (+ share rules)   [S2]
API /api/display-prefs ── DisplayPrefsService               [S3]
FE list groupBy label ── groupIssuesBy                      [S1]
FE Board swimlanes ── IssueBoard matrix                     [S3]
Hotkey L + picker ── E5 focus stack                         [S1]
```

## 4. Schema 草图

### 4.1 `tag_groups`（S1）

```text
tag_groups
  id            String(36) PK
  workspace_id  String(36) FK workspaces.id ON DELETE CASCADE NOT NULL
  name          String(64) NOT NULL
  color         String(20) NULL          # 组默认色（可选）
  position      Integer NOT NULL DEFAULT 0
  created_at    DateTime NOT NULL
  updated_at    DateTime NOT NULL

Indexes:
  ix_tag_groups_workspace_id
  uq_tag_groups_ws_name (workspace_id, name)
```

### 4.2 `tags` 扩展（S1）

```text
tags  (existing +)
  workspace_id  String(36) FK workspaces.id ON DELETE CASCADE  -- 迁移后 NOT NULL
  color         String(20) NOT NULL DEFAULT '#3b82f6'
  group_id      String(36) NULL FK tag_groups.id ON DELETE SET NULL
  -- name: drop global uq_tags_name; add uq_tags_ws_name (workspace_id, name)
```

回填策略（Q5）：见 roadmap；迁移脚本可幂等 inspect。

### 4.3 `issue_saved_views` 扩展（S2）

```text
issue_saved_views
  is_shared     Boolean NOT NULL DEFAULT false

Indexes:
  idx_saved_views_ws_shared (workspace_id, is_shared)   # 可选
```

语义：

- `is_shared=false`：仅 `owner_user_id` 可见可写（E4 行为）
- `is_shared=true`：同 workspace 全员（含 viewer）可读；写 = owner_user_id **或** workspace role=owner
- member 对共享视图：`POST /saved-views/{id}/save-as` → 复制为当前用户的个人视图（`is_shared=false`）

### 4.4 `issue_display_prefs`（S3）

```text
issue_display_prefs
  id            String(36) PK
  workspace_id  String(36) FK workspaces.id ON DELETE CASCADE NOT NULL
  user_id       String(36) NOT NULL
  display_json  JSON NOT NULL
  updated_at    DateTime NOT NULL

Unique: (workspace_id, user_id)
```

### 4.5 `display_json` 契约（S2 写入兼容；S3 用满）

```json
{
  "view_mode": "list",
  "group_by": "label",
  "swimlane_by": "assignee",
  "hide_empty_lanes": true,
  "fields": {
    "assignee": true,
    "priority": true,
    "labels": true,
    "estimate_points": false,
    "due_date": false,
    "project": false,
    "cycle": false,
    "issue_code": true,
    "type": false
  }
}
```

缺省：等同今日硬编码（board 显示 code+priority+title+assignee；list 列保持现状）。未知键忽略。

`group_by` 合法值：既有 + `'label'`。  
`swimlane_by`：`'none'|'assignee'|'priority'|'type'|'label'`（S3；list 的 group_by 与 board swimlane 独立键，避免 list/board 互相踩）。

## 5. API 草图

### 5.1 Tags（S1）— `/api/tags`

鉴权：`require_workspace_context`；写 member+；读 member（viewer 可读）。

| Method | Path | 行为 |
|---|---|---|
| GET | `/api/tags` | 当前 WS 标签；query：`group_id?` `q?` |
| POST | `/api/tags` | `{name, color?, group_id?}` |
| PATCH | `/api/tags/{id}` | 改 name/color/group |
| DELETE | `/api/tags/{id}` | 删标签（级联 issue_tags）；**无**复杂退休流 |
| GET/POST | `/api/tag-groups` | 组 CRUD（同权限） |

Issue 侧：

| Method | Path | 行为 |
|---|---|---|
| GET | `/api/issues/{id}/tags` | **恢复真实列表**（含 name/color/group） |
| PUT | `/api/issues/{id}/tags` | 可选：整体替换 id 列表（便于 L picker 一次提交） |
| POST/DELETE | `/api/issues/{id}/tags/{tag_id}` | 保留 |

`get_or_create_tag(db, name, workspace_id=…)`：Jira sync 必传 WS。

### 5.2 Saved Views（S2）— 扩展现有 `/api/saved-views`

| Method | Path | 行为 |
|---|---|---|
| GET | `` | 返回 `{ personal: [...], shared: [...] }` 或扁平 + `isShared`（FE 分区）；personal=我的；shared=`is_shared` 且同 WS |
| POST | `` | member+；body 可含 `is_shared`（viewer 403） |
| GET/PATCH/DELETE | `/{id}` | 读：accessible；写/删：个人仅 owner_user；共享仅 creator 或 WS owner |
| POST | `/{id}/favorite` | 仅对 **自己的** personal 或（可选）共享的「我的收藏元数据」—— **E7 默认：favorite 仅 personal**；共享收藏进 E8 Favorites |
| POST | `/{id}/save-as` | member+；body `{name?}`；深拷贝 filter/sort/display → 新 personal |

跨用户改他人 personal：404。viewer 对共享：可读不可写不可建。

### 5.3 Display prefs（S3）— `/api/display-prefs`

| Method | Path | 行为 |
|---|---|---|
| GET | `/api/display-prefs/issue` | 当前用户在 WS 的个人默认；无则 `data=null` |
| PUT | `/api/display-prefs/issue` | upsert `display_json` |

列表页加载顺序：URL/会话 → 若应用了 Saved View 用 View.display → 否则个人 prefs → 否则内置缺省。

## 6. 前端行为

### 6.1 S1

- 标签管理轻页或 Issue 筛选旁「标签」入口（可 `/workspace/labels`）
- 详情侧栏恢复加减标签
- `GROUP_BY_OPTIONS` + `groupIssuesBy` 支持 `label`（多标签展开；`__unlabelled__`）
- `L` → labels picker（搜索、勾选、确认写 PUT/POST）
- ⌘K：可选 `action.labels` 打开同一 picker（有焦点时）

### 6.2 S2

- Saved Views 下拉：分区「我的」/「共享」
- 保存对话框：可选「共享给工作区」
- 「另存为」按钮（共享只读成员）
- 权限错误 toast

### 6.3 S3

- Display 面板：字段开关；「设为个人默认」；「重置」
- Board：`swimlane_by` 选择器；空泳道隐藏开关；矩阵渲染（行 × status 列）
- 卡片按 `fields.*` 显隐
- 应用 View 时恢复 swimlane/fields；清除 View 回退 prefs

## 7. 测试计划（门禁）

### Backend

- Tag CRUD + 跨 WS 不可见/不可写
- 同 WS 重名 409；颜色/组更新
- Issue 打标 / 替换；GET tags 非空
- Jira sync 创建的 Tag 带 workspace_id（定向单测）
- Shared View：member 建共享；他员可读；非 creator member 写 403；owner 可写；他人 personal 404；Save As 产生 personal
- Display prefs upsert；与 View.display 并存不互相覆盖（服务层单测）

### Frontend

- `groupIssuesBy` label 展开单测
- `resolveIssueHotkeyAction` L 单测（editable/palette 忽略）
- `apply-saved-view` 认 `group_by: label` + 新键
- Board swimlane 纯函数：分桶 × 列、hide empty（S3）
- lint + build 0 errors

### 全量

- `uv run pytest tests/ -v`
- `npm run lint && npm run build`

## 8. Sprint 切分与依赖

```
E6-S3 tip (7dd7c55)
    └── E7-S1 Labels (+ L + groupBy label)     [docs 本批；impl 下批]
            └── E7-S2 Shared Views
                    └── E7-S3 Display + Swimlanes → Epic complete → E8
```

S1 **不**加 `is_shared`、**不**做 Board 泳道、**不做** display prefs 表（避免范围膨胀）。  
S2 可写 `display.group_by: label` 但不强制 fields/swimlane UI。  
S3 收口 Epic。

## 9. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 全局 Tag 名迁移冲突 | 幂等迁移 + 后缀；单测固定样例 |
| Jira sync 忘记传 workspace | 改签名强制 keyword-only `workspace_id`；旧调用失败于类型/单测 |
| 共享 View 误改 | 服务层统一 `assert_can_write_view`；负例必测 |
| Board 泳道性能 | 客户端对当前筛选结果分桶；不新增服务端矩阵 API |
| Epic 过厚 | 三 Sprint 内切；整包一次回执 |

## 10. 非目标重申

退休治理、Insights、强制唯一工作区布局、跨泳道拖拽改字段、E8 Favorites/Timeline、远程 push。

## 11. Self-review（本稿）

- 无 TBD 阻塞实现；Q1–Q5 已关闭
- 与 roadmap ADR D1–D14 一致
- S1/S2/S3 边界清晰；本 Phase 无产品代码
- `display_json` 新旧键兼容写明
