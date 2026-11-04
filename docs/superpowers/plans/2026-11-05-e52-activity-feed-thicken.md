# E52 Plan：Activity Feed 加厚 v2 — 关注过滤 · 行内反应 · 薄铃铛 · CLI 1.36.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`abb96db` · 分支 `sprint/E52-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e52-activity-feed-thicken-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E53**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Activity Feed 支持 `watching` 过滤、行内反应摘要/快捷 toggle（复用 E27）、薄未读铃铛（`activity_read_cursors` + unread-count）、CLI **1.36.0**；读路径 no-emit。

**Architecture:** 扩 `query_timeline_entries` 可选 `watcher_user_id`（join `issue_watchers`）；activity 序列化批量挂 reactions（issue 为主，payload.comment_id 则 comment）；新表 `activity_read_cursors` + `GET unread-count` + `POST mark-read`；FE 开关/空态/chips/铃铛；CLI `--watching` + `activity unread`。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E53；中文 docs；CLI **1.36.0**
- Q1a `watching` 对齐 E19；Q2a issue 反应为主 + comment_id 则 comment；Q3a 独立小表；Q4a 默认全量 Feed；Q5a 无 Push；Q6a 要 `activity unread`
- ADR D1–D7；E40 formula **永不** emit；不扩 E51 webhook pack；无 Redis/cron；无节假日
- 非目标见 design §2

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e52-activity-feed-thicken.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E52-acceptance.md`（骨架；收口补 tip/测数）

- [x] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A：`watching` 过滤（TDD）

**Files:**
- Modify: `backend/opentask/services/issue_timeline_export.py` — `query_timeline_entries(..., watcher_user_id: Optional[str]=None)`：当 set 时 `join IssueWatcher` 且 `IssueWatcher.user_id == watcher_user_id` 且 `IssueWatcher.workspace_id == workspace_id`
- Modify: `backend/opentask/api/issue/router.py` — `list_workspace_activity` 增 `watching: Optional[bool]=Query(None)`；`watching is True` 时传 `watcher_user_id=str(user.id)`
- Test: `backend/tests/api/test_e52_activity_feed_thicken.py`

**Interfaces:**
- Produces: `watching=true` 仅 watcher 集合；空 watcher → items=[]；可与 actionType/cursor 组合；跨租户不泄漏

- [x] **Step 1: 红测**
```python
# watch issue A only → activity watching=true 仅含 A 的行
# 无 watch → watching=true → items=[]
# watching 与 actionType 组合
# 他 WS watcher 不泄漏
# 默认无 watching 仍全量（E47 兼容）
# 读路径 spy：list 不 fire_webhooks / fire_automations
```
- [x] **Step 2: 最小实现 → 绿 → commit**

---

### Task 3 — B：反应摘要序列化（TDD）

**Files:**
- Modify: `backend/opentask/services/issue_timeline_export.py`
  - `build_reaction_summary(emoji_users: dict[str,list[str]], viewer_id: str) -> list[{emoji,count,myReacted}]`
  - `attach_activity_reactions(items, *, issue_reaction_maps, comment_reaction_maps, viewer_id)`：若 `payload.comment_id` 有 comment 反应用 scope=comment，否则 scope=issue
- Modify: `backend/opentask/api/issue/router.py` — list activity 后批量查 `IssueReaction` / `CommentReaction`，挂 `reactions: {scope, commentId?, summary}`
- Test: 同 `test_e52_activity_feed_thicken.py`

- [x] **Step 1: 红测 → 绿 → commit**

---

### Task 4 — C：已读水位 migration + unread-count + mark-read（TDD）

**Files:**
- Create: `backend/opentask/models/activity_read_cursor/model.py` — `ActivityReadCursor(user_id, workspace_id PK, last_seen_at, last_seen_id)`
- Create: `backend/opentask/models/activity_read_cursor/__init__.py`
- Modify: `backend/opentask/models/__init__.py` — 注册
- Create: `backend/alembic/versions/2026_11_05_4000-n0c1d2e3f4a8_activity_read_cursors.py`（revises `m9b0c1d2e3f7`）
- Modify: `backend/opentask/api/issue/router.py`
  - `GET /activity/unread-count?watching=true` → `{count:int, capped:bool}`；count>99 → return 99 + capped；仅 watching 范围（Q 默认 watching=true 语义：query 默认 True 或强制 watching）
  - `POST /activity/mark-read` body optional `{watching?:bool}` → 把水位设为当前可见最新一行（或 now + 空 id）
- 注意路由顺序：`/activity/unread-count` 与 `/activity/mark-read` 必须在 `/{issue_id}` 之前（已有 `/activity` 同级）

- [x] **Step 1: 红测 unread>0 → mark-read → 0；跨租户；cap 99+ → 绿 → commit**

---

### Task 5 — D：FE 开关 / chips / 铃铛（TDD）

**Files:**
- Modify: `frontend/src/utils/activityFeed.ts` — `watching?: boolean` in query；`ActivityItem.reactions`；helpers `emptyActivityDescription(watching, hasWatchesHint)`；`formatUnreadBadge(n)` → `''|'1'..'99'|'99+'`
- Modify: `frontend/src/utils/activityFeed.test.ts`
- Modify: `frontend/src/service/api/issue.ts` — fetch reactions field；`fetchActivityUnreadCount`；`markActivityRead`
- Modify: `frontend/src/views/activity/index.vue` — 「仅关注」NSwitch；读 `route.query.watching`；空态；行尾 reaction chips（toggle 既有 API）；onMounted mark-read
- Modify: `frontend/src/layouts/modules/global-sider/ActivityNav.vue` — 角标；click → `{name:'activity', query:{watching:'1'}}`；轮询/挂载拉 unread

- [x] **Step 1: vitest 红→绿 → commit**

---

### Task 6 — E：CLI **1.36.0**

**Files:**
- Bump **全部** `1.35.0` → `1.36.0`：pyproject / `__init__.py` / setup.py / VERSION / `opentask_cli.VERSION` + 全仓历史 version 断言
- Modify: `agent-harness/opentask-cli/opentask/core/activity.py` — `--watching`；`activity unread`
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py` — `activity_unread_count`
- Create: `agent-harness/opentask-cli/tests/test_e52_activity_thicken.py`

- [x] **Step 1: 红测 → 绿 → commit**

---

### Task 7 — F：门禁 + acceptance tip

- [x] BE 定向 `test_e52*` + `test_e47*` + `test_notif_prefs_reactions*` / watchers；全量记 passed（`test_user_search` flake 可记）
- [x] CLI 全绿；确认 pins **1.36.0**
- [x] FE vitest + build
- [x] 写 acceptance tip；STOP；不 push；不自开 E53

---

## Self-review
- A–F / ADR D1–D7 / Q1a–Q6a 均有 task
- 无 placeholder；路由顺序注意 unread/mark-read
- CLI 五处钉版 + 历史断言
