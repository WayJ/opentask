# E17 设计：E16 收口 · CLI 估点/容量 · 全局 Search

日期：2026-11-04（Asia/Shanghai）  
Epic：E17  
基线：`sprint/E16-S1` @ `b4ec445`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E17-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E18**。

## 1. 目标

### A. 收口 E16 缺口
1. 对本地 BE `:7377` 跑 `alembic upgrade head`（含孤儿 Default WS 迁移 `a1b2c3d4e5f9`）；确认 workspace list 无孤儿 id。
2. CLI：`issue` 读写 `estimate_points`；`cycle` 展示点容量/velocity（对齐 `/api/cycles/capacity-hint`）；单测 + README。

### B. 全局 Search（Linear Search）
- 统一搜索页：Issue（KEY-N/标题）/ Project / Doc（entity_documents）/ Member
- ⌘K 「搜索…」深链到 `/search?q=`
- 聚合 API：`GET /api/search?q=&limit=`，强制 `X-Workspace-Id` + membership
- FE：分组结果、键盘选择跳转；不改 DESIGN/Naive 主题令牌

## 2. 探索事实

| 项 | 现状 |
|---|---|
| 孤儿迁移 | `…_cleanup_orphan_default_workspace.py` 已在 tip，**未必已 apply 到 :7377 DB** |
| `estimate_points` | BE schema/列/详情 UX 已有；CLI create/update/show/list **未暴露** |
| Cycle 容量 | `GET /api/cycles/capacity-hint` 返回 `unit/suggestedCapacity/samples/currentLoad`；CLI **无 capacity 命令** |
| ⌘K | E5 已有实体搜索组（Issues/Projects/Views/Cycles）；**无独立 Search 页** |
| Doc | `entity_documents` 按 parent 列，无全局 title 搜索 |
| Member list | 仅 `userId/role`，搜索需 join `UserModel` |

## 3. 决策

| ID | 决策 |
|----|------|
| D1 | 聚合 API 新路由 `GET /api/search`，require_workspace_context；缺头 400；非成员 403 |
| D2 | 结果分组：`issues` / `projects` / `docs` / `members`；每组默认 limit=10（总 cap 可配） |
| D3 | Issue：title/issue_code/legacy_code ilike；若 q 像 KEY-N 则额外 by_code 精确优先 |
| D4 | Project：当前 WS 内 name ilike；Doc：entity_documents.title(+body 可选) ilike；Member：username/name/sso_name/sso_account ilike |
| D5 | FE `/search` hideInMenu，⌘K action「搜索…」→ `/search`（有 query 则带 `?q=`） |
| D6 | CLI `--estimate-points` on create/update；show/list 展示 Points；`cycle capacity [--cycle-id]` + show 附带 hint |
| D7 | CLI bump **1.2.0**；中文 design/plan/acceptance |
| D8 | 不 push；不换皮肤；不自开 E18 |

## 4. 非目标
- Knowledge-base 全文检索 / 向量搜索
- 替换 ⌘K 实体组（Search 页是补充深链）
- Velocity 图表 / burndown
- 改 IDOR 逻辑（保持 E15）

## 5. 验收摘要
- alembic head 已 apply；list 无 `00000000-0000-4000-8000-000000000001`
- CLI 可写读估点；`cycle capacity` 有 unit/suggested/samples
- `/api/search` 租户隔离 + 跨租户负例
- `/search` 分组+键盘跳转；⌘K 可进
- pytest 全绿；相关 vitest 绿
