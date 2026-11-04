# E47 Plan：WS Activity Feed v1 — JSON 游标 API · 薄 FE · CLI 1.31.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`5ab2400` · 分支 `sprint/E47-S1`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e47-workspace-activity-feed-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E48**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** 工作区级 **JSON 游标 Activity Feed**（`GET /api/issues/activity`）复用 `issue_timeline`；薄 FE `/activity` + Dashboard「查看全部活动」链；CLI **1.31.0** `activity list`；守 E40 D2/D7 **永不 emit**；无 migration。

**Architecture:** 从 E41 `build_timeline_csv` 抽取共享 `query_timeline_entries`（过滤语义对齐）；JSON 端叠加 `until`/`actorId`/cursor `(created_at,id)`；页默认 50 / 硬顶 clamp 200；FE 顶栏独立页；CLI 顶级 group。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E48；中文 docs；CLI **1.31.0**（`pyproject.toml` + `__init__.py` + `setup.py` + `opentask_cli.VERSION` 全钉）
- Q1a `/api/issues/activity`；Q2a clamp 200；Q3a FE `/activity`；Q4a Dashboard 不改短窗语义；Q5a `activity list`；Q6a 无索引 migration
- ADR D1–D9；E40 D2/D7 no-emit；无 Redis/cron
- 非目标见 design §3

## File map
| 区域 | 文件 |
|------|------|
| Shared query + JSON serialize | `backend/opentask/services/issue_timeline_export.py`（扩）或 `issue_activity.py` |
| API | `backend/opentask/api/issue/router.py` — `GET /activity` 靠近 `/timeline/export.csv` |
| FE page + nav | `frontend/src/views/activity/index.vue`；`layouts/.../ActivityNav.vue`；elegant routes/imports/types；locales |
| Dashboard 链 | `frontend/src/views/dashboard/index.vue` + `recent-activity.vue` |
| FE utils/API | `frontend/src/service/api/issue.ts`；`utils/activityFeed.ts` + vitest |
| CLI | `agent-harness/opentask-cli/opentask/core/activity.py`；`opentask_cli.py` register；api_client；version pins |
| Tests | `backend/tests/api/test_e47_workspace_activity_feed.py`；CLI `test_e47_*.py`；FE vitest |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E47-acceptance.md`（骨架；收口补 tip/测数）

- [x] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A：共享 query helper + cursor 编解码（TDD unit）

**Files:**
- Modify: `backend/opentask/services/issue_timeline_export.py`
  - `ACTIVITY_DEFAULT_LIMIT = 50`；`ACTIVITY_HARD_CAP = 200`
  - `encode_activity_cursor(created_at: datetime, id: str) -> str`（base64url `iso|id`）
  - `decode_activity_cursor(cursor: str) -> tuple[datetime, str]`；非法 → ValueError
  - `async def query_timeline_entries(db, *, workspace_id, issue_id=None, since=None, until=None, action_types=None, actor_id=None, cursor=None, limit=None) -> list[IssueTimeline]`
    - join Issue；`workspace_id` + `is_deleted==False`
    - filters: issue_id / since / until / action_types / actor_id(=user_id)
    - cursor：`(created_at, id) < (c_at, c_id)` 字典序倒序续页（`OR (created_at < c_at) OR (created_at == c_at AND id < c_id)`）
    - order `created_at.desc(), id.desc()`；`limit+1` 探测下一页
  - 重构 `build_timeline_csv` 调用 `query_timeline_entries`（无 until/actor/cursor；limit=CSV cap）保持语义
- Test: `backend/tests/api/test_e47_workspace_activity_feed.py` 先写 unit（cursor roundtrip + clamp 语义）

**Interfaces:**
- Produces: `query_timeline_entries` / `encode_activity_cursor` / `decode_activity_cursor` / caps

- [x] **Step 1: 红测** cursor roundtrip；非法 cursor ValueError；`_clamp_activity_limit(500)==200`；`_clamp_activity_limit(0)==1`
- [x] **Step 2: 绿 → commit**

---

### Task 3 — A：`GET /api/issues/activity` + 过滤/租户/spy（TDD）

**Files:**
- Modify: `issue_timeline_export.py` 增加 `serialize_activity_item(row, *, issue, actor_user) -> dict`（camelCase：id/issueId/issueCode/issueTitle/actionType/actor{id,username,displayName}/createdAt/payload）
- Modify: `backend/opentask/api/issue/router.py` 在 `/timeline/export.csv` 旁加：
```python
@router.get("/activity")
async def list_workspace_activity(
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
    actionType: Optional[List[str]] = Query(None),
    actorId: Optional[str] = Query(None),
    issueId: Optional[str] = Query(None),
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1),  # 超顶 clamp，不用 le=
    ...
):
```
  - 非法 ISO → 400；非法 actionType（非 TimelineAction）→ 400；cursor 非法 → 400
  - limit clamp 到 200
  - viewer+ via `require_workspace_context`
  - issueId 跨租户 → 404
  - 批量加载 Issue + User；`success_response(data={"items":..., "nextCursor": ...|null})`
  - **只读**；不写 timeline；不 fire

- [x] **Step 1: 红测**
  - 空 WS → items=[] nextCursor=null
  - 建 issue 改 status → feed 含 status_changed；含 issueCode
  - actionType / since / actorId / issueId 过滤
  - limit=500 → 返回 ≤200；cursor 第二页无重叠
  - 非法 actionType 400；跨 WS 不可见
  - spy：GET activity 期间 patch fire_webhooks / fire_automations / IssueService.add_timeline（或 append path）assert not called
- [x] **Step 2: 绿 → commit**
- [x] **Step 3:** E41 CSV 定向回归绿

---

### Task 4 — B：FE utils + API client（TDD vitest）

**Files:**
- Create: `frontend/src/utils/activityFeed.ts`
  - `ACTIVITY_ACTION_OPTIONS`；`buildActivityQuery(params)`（since24h/7d → ISO；actionTypes 数组；cursor；limit）
  - `formatActivityRow(item)` 复用 `formatTimelineAction`（payload→action_data）
- Create: `frontend/src/utils/activityFeed.test.ts`
- Modify: `frontend/src/service/api/issue.ts` 增加 `fetchWorkspaceActivity(params)`

- [x] **Step 1: 红测** buildActivityQuery 序列化；空态 format；since 快捷
- [x] **Step 2: 绿 → commit**

---

### Task 5 — B：`/activity` 页 + 顶栏 nav + Dashboard 链

**Files:**
- Create: `frontend/src/views/activity/index.vue`（过滤条 + 列表 + 加载更多；行点 Issue → `/issue/detail?id=`）
- Create: `frontend/src/layouts/modules/global-sider/ActivityNav.vue`（仿 InsightsNav）
- Modify: `global-sider/index.vue` 挂载 ActivityNav
- Modify: elegant `routes.ts` / `imports.ts` / `elegant-router.d.ts`；locales `route.activity`
- Modify: `dashboard/index.vue` Card header-extra「查看全部活动」→ `/activity`；**不**改 RecentActivity 数据语义
- Optional vitest：dashboard 链文案或 route name 存在（轻量）

- [x] **Step 1: 实现页+路由+链 → vitest 绿 → commit**

---

### Task 6 — C：CLI 1.31.0 `activity list`

**Files:**
- Create: `agent-harness/opentask-cli/opentask/core/activity.py`
```python
@click.group(name="activity")
def activity_cli(): ...

@activity_cli.command("list")
@click.option("--since")
@click.option("--action-type", multiple=True)
@click.option("--issue")
@click.option("--limit", default=50, type=int)
@click.option("--json", "as_json", is_flag=True)
```
- Modify: `api_client.py` `list_workspace_activity(**params)`
- Modify: `opentask_cli.py` `cli.add_command(activity_cli)`
- Bump **全部** version → **1.31.0**：pyproject / `__init__.py` / setup.py / VERSION；同步历史 `assert "1.30.0"` → `1.31.0`
- Test: `tests/test_e47_activity.py` — version；`activity list --help` 含 since/action-type/issue/limit/json

- [x] **Step 1: 红测 version/help → 绿 → commit**
- [x] **Step 2: 确认四文件均为 1.31.0**

---

### Task 7 — 门禁 + acceptance tip

- [x] BE full + `test_e47_*` + `test_e41_*` 定向
- [x] CLI full
- [x] FE vitest + `npm run build`
- [x] 写满 acceptance；最终 tip commit
- [x] **STOP**；不 push；不自开 E48

---

## Self-review
- Spec A–E / ADR D1–D9 / Q1–Q6 均有 task
- 无 placeholder；CLI 四钉 + 历史断言同步写明
- E41 CSV 通过共享 helper 保持同过滤语义
